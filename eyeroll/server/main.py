"""eyeroll hosted API server.

Routes:
    GET  /                    Serve landing page
    POST /signup              {email} → {api_key}
    POST /api/watch           {source, context?, max_frames?} → report string
    GET  /api/usage           → {used_today, limit, reset_at}
    POST /api/keys/rotate     {} → {api_key}

Run:
    uvicorn eyeroll.server.main:app --host 0.0.0.0 --port $PORT
"""

import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from .db import (
    RATE_LIMIT,
    check_rate_limit,
    create_user,
    get_user_by_key,
    init_pool,
    log_usage,
    rotate_key,
)

app = FastAPI(title="eyeroll API", docs_url=None, redoc_url=None)

_pool = None
_STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
async def _startup():
    global _pool
    _pool = await init_pool()


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def _auth(authorization: str = Header(default=None)) -> dict:
    """Validate Bearer token and return user row."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    api_key = authorization.removeprefix("Bearer ").strip()
    user = await get_user_by_key(_pool, api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return user


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def index():
    page = _STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"service": "eyeroll API", "signup": "/signup"})


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr


@app.post("/signup")
async def signup(body: SignupRequest):
    user = await create_user(_pool, body.email)
    return {"api_key": user["api_key"]}


# ---------------------------------------------------------------------------
# /api/watch
# ---------------------------------------------------------------------------

class WatchRequest(BaseModel):
    source: str
    context: str | None = None
    max_frames: int = 20


@app.post("/api/watch")
async def watch(body: WatchRequest, user: dict = Depends(_auth)):
    allowed, used = await check_rate_limit(_pool, user["id"])
    if not allowed:
        reset_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily rate limit reached.",
                "used_today": used,
                "limit": RATE_LIMIT,
                "reset_at": reset_at,
            },
        )

    try:
        report = await _run_analysis(body.source, body.context, body.max_frames)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    await log_usage(_pool, user["id"])
    return {"report": report}


async def _run_analysis(source: str, context: str | None, max_frames: int) -> str:
    """Run the eyeroll pipeline using the server's credentials."""
    import asyncio
    from eyeroll.watch import watch as run_watch

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(
        None,
        lambda: run_watch(
            source=source,
            context=context,
            max_frames=max_frames,
            backend_name=_pick_backend(),
            verbose=False,
            no_cache=False,
            parallel=3,
        ),
    )
    return report


def _pick_backend() -> str:
    """Choose cheapest available backend based on what keys are configured."""
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError(
        "No AI backend configured on server. Set GEMINI_API_KEY or OPENAI_API_KEY."
    )


# ---------------------------------------------------------------------------
# /api/usage
# ---------------------------------------------------------------------------

@app.get("/api/usage")
async def get_usage(user: dict = Depends(_auth)):
    from .db import usage_today
    used = await usage_today(_pool, user["id"])
    reset_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return {
        "used_today": used,
        "limit": RATE_LIMIT,
        "reset_at": reset_at,
    }


# ---------------------------------------------------------------------------
# /api/keys/rotate
# ---------------------------------------------------------------------------

@app.post("/api/keys/rotate")
async def rotate(user: dict = Depends(_auth)):
    new_key = await rotate_key(_pool, user["id"])
    return {"api_key": new_key}
