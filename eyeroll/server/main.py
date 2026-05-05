"""eyeroll hosted API server.

Auth is expected to be enforced by the deployment platform (for example,
TrueFoundry endpoint authentication). The app reads trusted identity headers for
logging/future history but does not manage users, signup, API keys, or quotas.

Routes
------
GET  /health                 Health check
POST /api/watch              {source, context?, max_frames?, repo_context?}
GET  /api/queue              Queue status

Run:
    uvicorn eyeroll.server.main:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="eyeroll API", docs_url=None, redoc_url=None)

_STATIC_DIR = Path(__file__).parent / "static"

# Concurrency limiter — at most N analyses run at once, rest queue up.
_MAX_CONCURRENT = int(os.environ.get("EYEROLL_MAX_CONCURRENT", "3"))
_analysis_sem = asyncio.Semaphore(_MAX_CONCURRENT)


# ---------------------------------------------------------------------------
# Platform identity
# ---------------------------------------------------------------------------

def _identity_from_headers(request: Request) -> dict:
    """Read identity claims injected by the hosting/auth layer, if present."""
    headers = request.headers
    return {
        "user_id": (
            headers.get("x-tfy-user-id")
            or headers.get("x-auth-request-user")
            or headers.get("x-forwarded-user")
        ),
        "email": (
            headers.get("x-tfy-user-email")
            or headers.get("x-auth-request-email")
            or headers.get("x-forwarded-email")
        ),
        "workspace_id": headers.get("x-tfy-workspace-id"),
    }


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def index():
    page = _STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"service": "eyeroll API", "watch": "/api/watch"})


@app.get("/health")
async def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# /api/watch
# ---------------------------------------------------------------------------

class WatchRequest(BaseModel):
    source: str
    context: str | None = None
    max_frames: int = 20
    repo_context: str | None = None


@app.post("/api/watch")
async def watch(request: Request):
    _identity_from_headers(request)
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
        repo_context = form.get("repo_context")

        tmp_dir = tempfile.mkdtemp(prefix="eyeroll_upload_")
        tmp_path = os.path.join(tmp_dir, uploaded.filename)
        with open(tmp_path, "wb") as f:
            f.write(await uploaded.read())

        try:
            report = await _run_analysis(tmp_path, context, max_frames, repo_context)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        # JSON body — source is a URL
        body = WatchRequest(**(await request.json()))
        try:
            report = await _run_analysis(body.source, body.context, body.max_frames, body.repo_context)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return _watch_response(report)


async def _run_analysis(
    source: str,
    context: str | None,
    max_frames: int,
    repo_context: str | None = None,
) -> str:
    from eyeroll.watch import watch as run_watch

    async with _analysis_sem:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: run_watch(
                source=source,
                context=context,
                codebase_context=repo_context,
                max_frames=max_frames,
                backend_name=_pick_backend(),
                verbose=False,
                no_cache=False,
                parallel=3,
            ),
        )


def _watch_response(report: str) -> dict:
    from eyeroll.watch import extract_metadata

    metadata = extract_metadata(report) or {}
    return {
        "report": report,
        "intent": metadata.get("intent") or metadata.get("content_type") or metadata.get("category", "other"),
        "repo_guess": metadata.get("repo_guess", "unknown"),
        "handoff_recommended": _as_bool(metadata.get("handoff_recommended") or metadata.get("actionable")),
        "confidence": metadata.get("confidence", "medium"),
    }


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"yes", "true", "1", "recommended"}


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
