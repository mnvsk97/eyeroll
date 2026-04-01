"""Main orchestrator — the /watch pipeline."""

import os
import shutil
import sys

from .acquire import acquire
from .analyze import (
    analyze_audio,
    analyze_frames,
    analyze_video_direct,
    synthesize_bug_report,
)
from .extract import (
    extract_audio,
    extract_key_frames,
    fmt_timestamp,
    get_video_duration,
    has_audio_track,
)

# Max file size for direct video upload to Gemini (20MB)
MAX_DIRECT_UPLOAD_MB = 20
# Max video duration for direct upload (2 minutes)
MAX_DIRECT_UPLOAD_SECONDS = 120


def watch(
    source: str,
    context: str | None = None,
    max_frames: int = 20,
    verbose: bool = False,
) -> str:
    """Full pipeline: acquire media → extract → analyze → report.

    Args:
        source: URL or local file path to video/image.
        context: Optional text context from the reporter (Slack message, issue body, etc.)
        max_frames: Maximum number of key frames to extract and analyze.
        verbose: Print progress to stderr.

    Returns:
        Markdown-formatted report.
    """
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
            return _analyze_image(file_path, context, title, verbose)
        else:
            return _analyze_video(file_path, context, title, max_frames, verbose)
    finally:
        # Clean up downloaded files (not local files)
        if media["source_url"]:
            parent = os.path.dirname(file_path)
            if parent.startswith("/tmp") or "eyeroll_" in parent:
                shutil.rmtree(parent, ignore_errors=True)


def _analyze_image(
    file_path: str,
    context: str | None,
    title: str,
    verbose: bool,
) -> str:
    """Analyze a single screenshot/image."""
    frames = [{
        "frame_path": file_path,
        "timestamp": 0.0,
        "frame_index": 0,
    }]

    frame_analyses = analyze_frames(frames, verbose=verbose)

    report = synthesize_bug_report(
        frame_analyses=frame_analyses,
        context=context,
        verbose=verbose,
    )

    return _wrap_report(report, title, "screenshot", context)


def _analyze_video(
    file_path: str,
    context: str | None,
    title: str,
    max_frames: int,
    verbose: bool,
) -> str:
    """Analyze a video file."""
    duration = get_video_duration(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if verbose:
        print(f"  Duration: {fmt_timestamp(duration)}", file=sys.stderr)
        print(f"  Size: {file_size_mb:.1f}MB", file=sys.stderr)

    # Decide strategy: direct upload vs frame-by-frame
    use_direct = (
        file_size_mb <= MAX_DIRECT_UPLOAD_MB
        and duration <= MAX_DIRECT_UPLOAD_SECONDS
    )

    video_analysis = None
    frame_analyses = None

    if use_direct:
        # Send full video to Gemini — better context, more accurate
        if verbose:
            print("  Strategy: direct video upload", file=sys.stderr)
        video_analysis = analyze_video_direct(file_path, duration, verbose=verbose)
    else:
        # Extract key frames and analyze individually
        if verbose:
            print("  Strategy: frame-by-frame analysis", file=sys.stderr)
        frames = extract_key_frames(file_path, max_frames=max_frames)
        if verbose:
            print(f"  Extracted {len(frames)} key frames", file=sys.stderr)
        frame_analyses = analyze_frames(frames, verbose=verbose)

        # Clean up frame files
        if frames:
            frame_dir = os.path.dirname(frames[0]["frame_path"])
            shutil.rmtree(frame_dir, ignore_errors=True)

    # Audio transcription (if available)
    transcript = None
    if has_audio_track(file_path):
        audio_path = extract_audio(file_path)
        if audio_path:
            transcript = analyze_audio(audio_path, verbose=verbose)
            if transcript and "[no speech detected]" in transcript.lower():
                transcript = None
            # Clean up audio file
            audio_dir = os.path.dirname(audio_path)
            shutil.rmtree(audio_dir, ignore_errors=True)

    report = synthesize_bug_report(
        frame_analyses=frame_analyses,
        video_analysis=video_analysis,
        transcript=transcript,
        context=context,
        verbose=verbose,
    )

    return _wrap_report(report, title, f"video ({fmt_timestamp(duration)})", context)


def _wrap_report(
    report: str,
    title: str,
    media_type: str,
    context: str | None,
) -> str:
    """Add metadata header to the report."""
    header = f"# eyeroll: {title}\n"
    header += f"**Source type:** {media_type}\n"
    if context:
        header += f"**Context:** {context}\n"
    header += "\n---\n\n"
    return header + report
