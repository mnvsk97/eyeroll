"""eyeroll hosted API server.

Routes
------
GET  /                       Landing page
POST /signup                 {email} → {api_key, key_id, key_name}

GET  /api/keys               List all API keys for the authenticated user
POST /api/keys               {name?} → create a new key
PATCH /api/keys/{key_id}     {name} → rename a key
DELETE /api/keys/{key_id}    Revoke a key (must have ≥1 remaining)

POST /api/watch              {source, context?, max_frames?} → {report}
GET  /api/usage              → {used_today, limit, reset_at}

Run:
    uvicorn eyeroll.server.main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, Header, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from .db import (
    RATE_LIMIT,
    check_rate_limit,
    create_key,
    create_user,
    delete_key,
    get_user_by_key,
    init_pool,
    list_keys,
    log_usage,
    rename_key,
    usage_today,
)

app = FastAPI(title="eyeroll API", docs_url=None, redoc_url=None)

_pool = None
_STATIC_DIR = Path(__file__).parent / "static"

# Concurrency limiter — at most N analyses run at once, rest queue up.
_MAX_CONCURRENT = int(os.environ.get("EYEROLL_MAX_CONCURRENT", "3"))
_analysis_sem = asyncio.Semaphore(_MAX_CONCURRENT)


@app.on_event("startup")
async def _startup():
    global _pool
    _pool = await init_pool()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

async def _auth(authorization: str = Header(default=None)) -> dict:
    """Validate Bearer token. Returns {user_id, email, key_id}."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    raw_key = authorization.removeprefix("Bearer ").strip()
    ctx = await get_user_by_key(_pool, raw_key)
    if not ctx:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    return ctx


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
    """Create account. Returns the default API key for new users only."""
    key, is_new = await create_user(_pool, body.email)
    if not is_new:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Use your existing API key.",
        )
    return {
        "api_key": key["key"],
        "key_id": key["id"],
        "key_name": key["name"],
    }


# ---------------------------------------------------------------------------
# Key CRUD  /api/keys
# ---------------------------------------------------------------------------

class CreateKeyRequest(BaseModel):
    name: str = "default"


class RenameKeyRequest(BaseModel):
    name: str


@app.get("/api/keys")
async def keys_list(ctx: dict = Depends(_auth)):
    """List all API keys for the authenticated user."""
    rows = await list_keys(_pool, ctx["user_id"])
    return {
        "keys": [
            {"id": r["id"], "name": r["name"], "key": r["key"], "created_at": str(r["created_at"])}
            for r in rows
        ]
    }


@app.post("/api/keys", status_code=201)
async def keys_create(body: CreateKeyRequest, ctx: dict = Depends(_auth)):
    """Create a new API key for the authenticated user."""
    row = await create_key(_pool, ctx["user_id"], body.name)
    return {"api_key": row["key"], "key_id": row["id"], "key_name": row["name"]}


@app.patch("/api/keys/{key_id}")
async def keys_rename(key_id: str, body: RenameKeyRequest, ctx: dict = Depends(_auth)):
    """Rename an API key."""
    updated = await rename_key(_pool, ctx["user_id"], key_id, body.name)
    if not updated:
        raise HTTPException(status_code=404, detail="Key not found.")
    return {"id": updated["id"], "name": updated["name"], "key": updated["key"]}


@app.delete("/api/keys/{key_id}", status_code=204)
async def keys_delete(key_id: str, ctx: dict = Depends(_auth)):
    """Revoke an API key. At least one key must remain."""
    try:
        deleted = await delete_key(_pool, ctx["user_id"], key_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found.")


# ---------------------------------------------------------------------------
# /api/watch
# ---------------------------------------------------------------------------

class WatchRequest(BaseModel):
    source: str
    context: str | None = None
    max_frames: int = 20


@app.post("/api/watch")
async def watch(request: Request, ctx: dict = Depends(_auth)):
    allowed, used = await check_rate_limit(_pool, ctx["user_id"])
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

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # File upload — save to temp dir and analyze
        import tempfile
        form = await request.form()
        uploaded: UploadFile = form.get("file")
        if not uploaded:
            raise HTTPException(status_code=400, detail="Missing 'file' in multipart upload.")
        context = form.get("context")
        max_frames = int(form.get("max_frames", "20"))

        tmp_dir = tempfile.mkdtemp(prefix="eyeroll_upload_")
        tmp_path = os.path.join(tmp_dir, uploaded.filename)
        with open(tmp_path, "wb") as f:
            f.write(await uploaded.read())

        try:
            report = await _run_analysis(tmp_path, context, max_frames)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        # JSON body — source is a URL
        body = WatchRequest(**(await request.json()))
        try:
            report = await _run_analysis(body.source, body.context, body.max_frames)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    await log_usage(_pool, ctx["user_id"], ctx["key_id"])
    return {"report": report}


async def _run_analysis(source: str, context: str | None, max_frames: int) -> str:
    from eyeroll.watch import watch as run_watch

    async with _analysis_sem:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
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


# ---------------------------------------------------------------------------
# /api/try  — anonymous, IP-rate-limited
# ---------------------------------------------------------------------------

_try_usage: dict[str, list] = {}  # ip -> [timestamps]
_TRY_LIMIT = 3  # per IP per day


def _check_try_limit(ip: str) -> bool:
    """Return True if the IP is under the anonymous try limit."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    hits = _try_usage.get(ip, [])
    hits = [t for t in hits if t > cutoff]
    _try_usage[ip] = hits
    return len(hits) < _TRY_LIMIT


@app.post("/api/try")
async def try_watch(request: Request):
    """Anonymous video analysis — no API key needed. 3/day per IP."""
    ip = request.client.host if request.client else "unknown"
    if not _check_try_limit(ip):
        raise HTTPException(status_code=429, detail="Daily try limit reached (3/day). Sign up for more.")

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        import tempfile
        form = await request.form()
        uploaded: UploadFile = form.get("file")
        if not uploaded:
            raise HTTPException(status_code=400, detail="Missing 'file' in upload.")
        context = form.get("context")
        max_frames = int(form.get("max_frames", "20"))

        tmp_dir = tempfile.mkdtemp(prefix="eyeroll_try_")
        tmp_path = os.path.join(tmp_dir, uploaded.filename)
        with open(tmp_path, "wb") as f:
            f.write(await uploaded.read())

        try:
            report = await _run_analysis(tmp_path, context, max_frames)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        body = WatchRequest(**(await request.json()))
        try:
            report = await _run_analysis(body.source, body.context, body.max_frames)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    _try_usage.setdefault(ip, []).append(datetime.now(timezone.utc))
    return {"report": report}


@app.get("/api/queue")
async def queue_status():
    """Check how busy the analysis queue is."""
    # _analysis_sem._value is the number of remaining slots
    active = _MAX_CONCURRENT - _analysis_sem._value
    waiting = max(0, len(getattr(_analysis_sem, '_waiters', [])))
    return {
        "active": active,
        "waiting": waiting,
        "max_concurrent": _MAX_CONCURRENT,
    }


def _pick_backend() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError("No AI backend configured. Set GEMINI_API_KEY or OPENAI_API_KEY.")


# ---------------------------------------------------------------------------
# /api/usage
# ---------------------------------------------------------------------------

@app.get("/api/usage")
async def get_usage(ctx: dict = Depends(_auth)):
    used = await usage_today(_pool, ctx["user_id"])
    reset_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return {"used_today": used, "limit": RATE_LIMIT, "reset_at": reset_at}
