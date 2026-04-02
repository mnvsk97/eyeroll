"""Main orchestrator — the /watch pipeline."""

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

from .acquire import acquire
from .analyze import (
    analyze_audio,
    analyze_frames,
    analyze_video_direct,
    synthesize_report,
)
from .backend import get_backend, reset_backend
from .extract import (
    extract_audio,
    extract_key_frames,
    fmt_timestamp,
    get_video_duration,
    has_audio_track,
)

# Max file size for direct video upload (20MB)
MAX_DIRECT_UPLOAD_MB = 20
# Max video duration for direct upload (2 minutes)
MAX_DIRECT_UPLOAD_SECONDS = 120


def watch(
    source: str,
    context: str | None = None,
    codebase_context: str | None = None,
    max_frames: int = 20,
    backend_name: str | None = None,
    model: str | None = None,
    verbose: bool = False,
    no_cache: bool = False,
    parallel: int = 1,
) -> str:
    """Full pipeline: acquire media -> extract -> analyze -> report.

    Args:
        source: URL or local file path to video/image.
        context: Optional text context (Slack message, issue body, etc.)
        codebase_context: Optional codebase context (project structure, stack, key files).
        max_frames: Maximum number of key frames to extract and analyze.
        backend_name: 'gemini', 'openai', or 'ollama'. Defaults to EYEROLL_BACKEND env var, then 'gemini'.
        model: Model override (e.g., 'qwen3-vl:8b' for ollama, 'gemini-2.0-flash' for gemini).
        verbose: Print progress to stderr.
        no_cache: Skip cache lookup and force fresh analysis.
        parallel: Number of concurrent workers for frame analysis (default: 1 = sequential).

    Returns:
        Markdown-formatted report.
    """
    # Build backend kwargs
    backend_kwargs = {}
    if model:
        backend_kwargs["model"] = model

    # Initialize backend early to fail fast on config errors
    backend = get_backend(backend_name, **backend_kwargs)
    backend_label = backend_name or os.environ.get("EYEROLL_BACKEND", "gemini")

    if verbose:
        print(f"Backend: {backend_label}", file=sys.stderr)
        if model:
            print(f"Model: {model}", file=sys.stderr)
        if codebase_context:
            print("  Codebase context provided", file=sys.stderr)

    # Check cache for intermediate results
    cache_key = _cache_key(source, backend_label, model)
    if not no_cache:
        cached = _cache_load(cache_key)
        if cached:
            if verbose:
                print("  Cache hit — reusing cached analysis, re-running synthesis", file=sys.stderr)
            # Re-run synthesis with current context/codebase_context
            report = synthesize_report(
                frame_analyses=cached.get("frame_analyses"),
                video_analysis=cached.get("video_analysis"),
                transcript=cached.get("transcript"),
                context=context,
                codebase_context=codebase_context,
                verbose=verbose,
            )
            return _wrap_report(report, cached["title"], cached["media_type"], context, backend_label)

    # Step 1: Acquire
    if verbose:
        print(f"Acquiring: {source}", file=sys.stderr)

    media = acquire(source)
    file_path = media["file_path"]
    media_type = media["media_type"]
    title = media["title"]

    if verbose:
        print(f"  Media type: {media_type}", file=sys.stderr)
        print(f"  Title: {title}", file=sys.stderr)
        print(f"  Path: {file_path}", file=sys.stderr)

    try:
        if media_type == "image":
            intermediates = _analyze_image(file_path, title, backend_label, verbose, parallel)
        else:
            intermediates = _analyze_video(
                file_path, title, max_frames, backend, backend_label, verbose, parallel,
            )

        # Cache intermediates (before synthesis)
        _cache_save(cache_key, source, intermediates)

        # Synthesis always runs fresh with current context
        report = synthesize_report(
            frame_analyses=intermediates["frame_analyses"],
            video_analysis=intermediates["video_analysis"],
            transcript=intermediates["transcript"],
            context=context,
            codebase_context=codebase_context,
            verbose=verbose,
        )
        return _wrap_report(report, title, intermediates["media_type"], context, backend_label)
    finally:
        # Clean up downloaded files (not local files)
        if media["source_url"]:
            parent = os.path.dirname(file_path)
            if parent.startswith("/tmp") or "eyeroll_" in parent:
                shutil.rmtree(parent, ignore_errors=True)
        reset_backend()


def _analyze_image(
    file_path: str,
    title: str,
    backend_label: str,
    verbose: bool,
    parallel: int = 1,
) -> dict:
    """Analyze a single screenshot/image. Returns intermediates dict."""
    frames = [{
        "frame_path": file_path,
        "timestamp": 0.0,
        "frame_index": 0,
    }]

    frame_analyses = analyze_frames(frames, verbose=verbose, parallel=parallel)

    return {
        "title": title,
        "media_type": "screenshot",
        "frame_analyses": frame_analyses,
        "video_analysis": None,
        "transcript": None,
    }


def _analyze_video(
    file_path: str,
    title: str,
    max_frames: int,
    backend,
    backend_label: str,
    verbose: bool,
    parallel: int = 1,
) -> dict:
    """Analyze a video file. Returns intermediates dict."""
    duration = get_video_duration(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if verbose:
        print(f"  Duration: {fmt_timestamp(duration)}", file=sys.stderr)
        print(f"  Size: {file_size_mb:.1f}MB", file=sys.stderr)

    # Decide strategy: direct upload vs frame-by-frame
    # Only use direct upload if backend supports it AND video is small enough
    use_direct = (
        backend.supports_video
        and file_size_mb <= MAX_DIRECT_UPLOAD_MB
        and duration <= MAX_DIRECT_UPLOAD_SECONDS
    )

    video_analysis = None
    frame_analyses = None

    if use_direct:
        if verbose:
            print("  Strategy: direct video upload", file=sys.stderr)
        video_analysis = analyze_video_direct(file_path, duration, verbose=verbose)
    else:
        if verbose:
            reason = "backend doesn't support video" if not backend.supports_video else "video too large"
            print(f"  Strategy: frame-by-frame ({reason})", file=sys.stderr)
        frames = extract_key_frames(file_path, max_frames=max_frames)
        if verbose:
            print(f"  Extracted {len(frames)} key frames", file=sys.stderr)
        frame_analyses = analyze_frames(frames, verbose=verbose, parallel=parallel)

        # Clean up frame files
        if frames:
            frame_dir = os.path.dirname(frames[0]["frame_path"])
            shutil.rmtree(frame_dir, ignore_errors=True)

    # Audio transcription (only if backend supports it)
    transcript = None
    if backend.supports_audio and has_audio_track(file_path):
        audio_path = extract_audio(file_path)
        if audio_path:
            transcript = analyze_audio(audio_path, verbose=verbose)
            if transcript and "[no speech detected]" in transcript.lower():
                transcript = None
            audio_dir = os.path.dirname(audio_path)
            shutil.rmtree(audio_dir, ignore_errors=True)
    elif verbose and not backend.supports_audio:
        print("  Skipping audio (not supported by this backend)", file=sys.stderr)

    return {
        "title": title,
        "media_type": f"video ({fmt_timestamp(duration)})",
        "frame_analyses": frame_analyses,
        "video_analysis": video_analysis,
        "transcript": transcript,
    }


def _wrap_report(
    report: str,
    title: str,
    media_type: str,
    context: str | None,
    backend_label: str,
) -> str:
    """Add metadata header to the report."""
    header = f"# eyeroll: {title}\n"
    header += f"**Source type:** {media_type}\n"
    header += f"**Backend:** {backend_label}\n"
    if context:
        header += f"**Context:** {context}\n"
    header += "\n---\n\n"
    return header + report


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

CACHE_DIR = os.path.join(".eyeroll", "cache")


def _cache_key(source: str, backend: str, model: str | None) -> str:
    """Generate a cache key from source + backend + model."""
    # For local files, hash file content; for URLs, hash the URL
    if os.path.isfile(source):
        with open(source, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        key_input = f"{file_hash}:{backend}:{model or 'default'}"
    else:
        key_input = f"{source}:{backend}:{model or 'default'}"
    return hashlib.sha256(key_input.encode()).hexdigest()[:16]


def _cache_load(key: str) -> dict | None:
    """Load cached intermediates if they exist.

    Returns a dict with keys: source, title, media_type, frame_analyses,
    video_analysis, transcript — or None if no cache entry exists.
    """
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.isfile(cache_path):
        try:
            with open(cache_path) as f:
                data = json.load(f)
            # Verify it's the new intermediate format (has 'media_type' key)
            if "media_type" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _cache_save(key: str, source: str, intermediates: dict) -> None:
    """Save intermediate analysis results to cache.

    Args:
        key: Cache key.
        source: Original source (URL or file path).
        intermediates: Dict with title, media_type, frame_analyses,
            video_analysis, transcript.
    """
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_data = {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key": key,
            "title": intermediates["title"],
            "media_type": intermediates["media_type"],
            "frame_analyses": intermediates.get("frame_analyses"),
            "video_analysis": intermediates.get("video_analysis"),
            "transcript": intermediates.get("transcript"),
        }
        with open(os.path.join(CACHE_DIR, f"{key}.json"), "w") as f:
            json.dump(cache_data, f, indent=2)
    except OSError:
        pass  # cache write failure is not fatal
