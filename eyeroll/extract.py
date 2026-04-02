"""Extract key frames and audio from video files using ffmpeg."""

import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


@functools.lru_cache(maxsize=1)
def _get_ffmpeg() -> str:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "ffmpeg not found. Install with: brew install ffmpeg"
        ) from exc


def get_video_duration(video_path: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_format", video_path],
            capture_output=True, text=True, check=True,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])

    ffmpeg = _get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, "-i", video_path],
        capture_output=True, text=True, check=False,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration of {video_path}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def has_audio_track(video_path: str) -> bool:
    """Check if a video file contains an audio stream."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return False
    result = subprocess.run(
        [ffprobe, "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=codec_type",
         "-print_format", "json", video_path],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return False
    try:
        info = json.loads(result.stdout)
        return len(info.get("streams", [])) > 0
    except json.JSONDecodeError:
        return False


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------
#
# Strategy:
#   1. Extract 1 frame every 2 seconds (covers the full video)
#   2. Remove near-duplicate frames by comparing file sizes
#      (frames that look similar compress to similar JPEG sizes)
#   3. Boost contrast so local models can read text better
#   4. Cap at max_frames
#
# This gives us 8-15 meaningful frames for a typical 30s-2min video,
# without needing opencv or any extra dependencies.
# ---------------------------------------------------------------------------

# Minimum JPEG size difference (bytes) to consider frames "different"
MIN_SIZE_DELTA = 5000


def extract_key_frames(
    video_path: str,
    max_frames: int = 20,
    output_dir: str | None = None,
    enhance: bool = True,
) -> list[dict]:
    """Extract key frames from a video.

    Extracts 1 frame every 2 seconds, removes near-duplicates,
    and optionally enhances contrast for better text readability.

    Returns list of dicts with keys: frame_path, timestamp, frame_index.
    """
    ffmpeg = _get_ffmpeg()
    duration = get_video_duration(video_path)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="eyeroll_frames_")

    # Step 1: Extract 1 frame every 2 seconds
    interval = 2.0
    num_candidates = max(1, int(duration / interval))
    candidates = []

    # Build ffmpeg filter: boost contrast if enhance=True
    vf_filter = "eq=contrast=1.3:brightness=0.05" if enhance else None

    for i in range(num_candidates):
        timestamp = i * interval
        frame_path = os.path.join(output_dir, f"raw_{i:03d}.jpg")

        cmd = [ffmpeg, "-y", "-ss", str(timestamp), "-i", video_path,
               "-vframes", "1", "-q:v", "2"]
        if vf_filter:
            cmd += ["-vf", vf_filter]
        cmd.append(frame_path)

        subprocess.run(cmd, capture_output=True, check=False)

        if os.path.isfile(frame_path) and os.path.getsize(frame_path) > 0:
            candidates.append({
                "frame_path": frame_path,
                "timestamp": timestamp,
                "size": os.path.getsize(frame_path),
            })

    if not candidates:
        return []

    # Step 2: Remove near-duplicate frames
    # Keep a frame if its file size differs enough from the previous kept frame.
    # JPEG size is a rough proxy for visual content — similar screens compress similarly.
    kept = [candidates[0]]  # always keep first frame
    for c in candidates[1:]:
        size_delta = abs(c["size"] - kept[-1]["size"])
        if size_delta > MIN_SIZE_DELTA:
            kept.append(c)

    # Always keep the last frame (often shows the final state / error)
    if len(candidates) > 1 and kept[-1] is not candidates[-1]:
        kept.append(candidates[-1])

    # Step 3: Cap at max_frames (keep evenly distributed if too many)
    if len(kept) > max_frames:
        step = len(kept) / max_frames
        kept = [kept[int(i * step)] for i in range(max_frames)]

    # Step 4: Rename and reindex
    frames = []
    for i, k in enumerate(kept):
        final_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")
        os.rename(k["frame_path"], final_path)
        frames.append({
            "frame_path": final_path,
            "timestamp": k["timestamp"],
            "frame_index": i,
        })

    # Clean up unused candidate frames
    for c in candidates:
        try:
            os.remove(c["frame_path"])
        except OSError:
            pass

    return frames


def extract_audio(video_path: str, output_dir: str | None = None) -> str | None:
    """Extract audio track as mp3. Returns path or None if no audio."""
    if not has_audio_track(video_path):
        return None

    ffmpeg = _get_ffmpeg()
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="eyeroll_audio_")

    audio_path = os.path.join(output_dir, "audio.mp3")
    result = subprocess.run(
        [
            ffmpeg, "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "4",
            audio_path,
        ],
        capture_output=True,
        check=False,
    )

    if result.returncode == 0 and os.path.isfile(audio_path):
        # Check if audio has actual content (not just silence)
        if os.path.getsize(audio_path) > 1024:
            return audio_path

    return None


def fmt_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
