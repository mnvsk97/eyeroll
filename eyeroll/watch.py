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
    analyze_temporal,
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

# Max file size for direct video upload via Gemini File API (2GB)
MAX_DIRECT_UPLOAD_MB = 2000
# Max video duration for direct upload (1 hour)
MAX_DIRECT_UPLOAD_SECONDS = 3600


def watch(
    source: str,
    context: str | None = None,
    codebase_context: str | None = None,
    max_frames: int = 20,
    backend_name: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
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
        backend_name: Backend name (e.g. 'gemini', 'openai', 'groq', 'openai-compat').
                      Defaults to EYEROLL_BACKEND env var, then 'gemini'.
        model: Model override (e.g., 'qwen3-vl:8b' for ollama, 'gemini-2.0-flash' for gemini).
        base_url: Base URL for openai-compat backend (e.g. https://my-server/v1).
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
    if base_url:
        backend_kwargs["base_url"] = base_url

    # Initialize backend early to fail fast on config errors
    backend = get_backend(backend_name, **backend_kwargs)
    backend_label = backend_name or os.environ.get("EYEROLL_BACKEND", "gemini")

    # Preflight: verify backend is reachable and discover capabilities
    from .backend import AnalysisError
    flight = backend.preflight()
    if not flight["healthy"]:
        raise AnalysisError(f"Backend {backend_label} is not reachable: {flight['error']}")

    if verbose:
        print(f"Backend: {backend_label}", file=sys.stderr)
        if model:
            print(f"Model: {model}", file=sys.stderr)
        caps = flight["capabilities"]
        print(f"  Capabilities: video_upload={caps['video_upload']}, "
              f"batch_frames={caps['batch_frames']}, audio={caps['audio']}", file=sys.stderr)
        if codebase_context:
            print("  Codebase context provided", file=sys.stderr)

    # Check cache for intermediate results
    cache_key = _cache_key(source, backend_label, model)
    if not no_cache:
        cached = _cache_load(cache_key)
        if cached:
            if verbose:
                print("  Cache hit — reusing cached analysis, re-running temporal synthesis", file=sys.stderr)
            temporal = analyze_temporal(
                frame_analyses=cached.get("frame_analyses"),
                video_analysis=cached.get("video_analysis"),
                transcript=cached.get("transcript"),
                context=context,
                codebase_context=codebase_context,
                verbose=verbose,
            )
            report = synthesize_report(
                past=temporal["past"],
                present=temporal["present"],
                future=temporal["future"],
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

        # Cache intermediates (before temporal analysis)
        _cache_save(cache_key, source, intermediates)

        # Temporal analysis runs fresh — past/present/future are context-dependent
        temporal = analyze_temporal(
            frame_analyses=intermediates["frame_analyses"],
            video_analysis=intermediates["video_analysis"],
            transcript=intermediates["transcript"],
            context=context,
            codebase_context=codebase_context,
            verbose=verbose,
        )

        report = synthesize_report(
            past=temporal["past"],
            present=temporal["present"],
            future=temporal["future"],
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

    # Decide strategy based on backend capabilities
    caps = backend.preflight()["capabilities"]
    max_mb = caps.get("max_video_mb") or MAX_DIRECT_UPLOAD_MB
    can_direct = caps["video_upload"] and file_size_mb <= max_mb and duration <= MAX_DIRECT_UPLOAD_SECONDS
    can_batch = caps["batch_frames"]

    video_analysis = None
    frame_analyses = None

    if can_direct:
        if verbose:
            print("  Strategy: direct video upload", file=sys.stderr)
        video_analysis = analyze_video_direct(file_path, duration, verbose=verbose)
    elif can_batch:
        if verbose:
            print("  Strategy: multi-frame batch (single API call)", file=sys.stderr)
        frames = extract_key_frames(file_path, max_frames=max_frames)
        if verbose:
            print(f"  Extracted {len(frames)} key frames", file=sys.stderr)
        frame_tuples = [(f["frame_path"], f["timestamp"]) for f in frames]
        from .analyze import BATCH_FRAMES_PROMPT
        video_analysis = backend.analyze_frames_batch(frame_tuples, BATCH_FRAMES_PROMPT, verbose=verbose)
        if frames:
            frame_dir = os.path.dirname(frames[0]["frame_path"])
            shutil.rmtree(frame_dir, ignore_errors=True)
    else:
        if verbose:
            print("  Strategy: frame-by-frame", file=sys.stderr)
        frames = extract_key_frames(file_path, max_frames=max_frames)
        if verbose:
            print(f"  Extracted {len(frames)} key frames", file=sys.stderr)
        frame_analyses = analyze_frames(frames, verbose=verbose, parallel=parallel)
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
    # Extract metadata block from the report if present
    metadata = _extract_metadata(report)

    header = f"# eyeroll: {title}\n"
    header += f"**Source type:** {media_type}\n"
    header += f"**Backend:** {backend_label}\n"
    if context:
        header += f"**Context:** {context}\n"
    if metadata:
        header += f"**Category:** {metadata.get('category', 'other')}\n"
        header += f"**Confidence:** {metadata.get('confidence', 'medium')}\n"
        header += f"**Scope:** {metadata.get('scope', 'out-of-context')}\n"
        header += f"**Severity:** {metadata.get('severity', 'low')}\n"
        header += f"**Actionable:** {metadata.get('actionable', 'no')}\n"
    header += "\n---\n\n"
    return header + report


def _extract_metadata(report: str) -> dict | None:
    """Parse the metadata code block from the synthesis report."""
    import re
    match = re.search(r"```\s*\n(category:.*?)```", report, re.DOTALL)
    if not match:
        return None
    metadata = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


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
