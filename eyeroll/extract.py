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


def extract_key_frames(
    video_path: str,
    max_frames: int = 20,
    output_dir: str | None = None,
    scene_detection: bool = True,
    scene_threshold: float = 0.15,
) -> list[dict]:
    """Extract key frames from a video.

    Uses ffmpeg scene detection to pick frames where the screen changes.
    Falls back to even-spaced intervals if scene detection finds too few frames.

    Returns list of dicts with keys: frame_path, timestamp, frame_index.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="eyeroll_frames_")

    frames = []
    if scene_detection:
        frames = _extract_scene_frames(video_path, max_frames, scene_threshold, output_dir)

    # Fallback to even-spaced if scene detection returned too few frames
    if len(frames) < 3:
        # Clean up any scene detection output
        for f in frames:
            try:
                os.remove(f["frame_path"])
            except OSError:
                pass
        frames = _extract_even_frames(video_path, max_frames, output_dir)

    return frames


def _extract_scene_frames(
    video_path: str,
    max_frames: int,
    threshold: float,
    output_dir: str,
) -> list[dict]:
    """Extract frames at scene changes using ffmpeg's scene detection filter."""
    ffmpeg = _get_ffmpeg()

    # Use ffmpeg scene filter to output frames + timestamps
    result = subprocess.run(
        [
            ffmpeg, "-y",
            "-i", video_path,
            "-vf", f"select='gt(scene\\,{threshold})',showinfo",
            "-vsync", "vfr",
            "-q:v", "2",
            "-frame_pts", "1",
            os.path.join(output_dir, "scene_%03d.jpg"),
        ],
        capture_output=True, text=True, check=False,
    )

    if result.returncode != 0:
        return []

    # Parse timestamps from showinfo output
    timestamps = _parse_showinfo_timestamps(result.stderr)

    # Collect the output files
    frames = []
    for i, fpath in enumerate(sorted(Path(output_dir).glob("scene_*.jpg"))):
        if i >= max_frames:
            break
        if fpath.stat().st_size > 0:
            ts = timestamps[i] if i < len(timestamps) else 0.0
            frames.append({
                "frame_path": str(fpath),
                "timestamp": ts,
                "frame_index": i,
            })

    return frames


def _parse_showinfo_timestamps(stderr: str) -> list[float]:
    """Parse pts_time values from ffmpeg showinfo filter output."""
    timestamps = []
    for match in re.finditer(r"pts_time:\s*([\d.]+)", stderr):
        timestamps.append(float(match.group(1)))
    return timestamps


def _extract_even_frames(
    video_path: str,
    max_frames: int,
    output_dir: str,
) -> list[dict]:
    """Extract frames at even intervals (original approach)."""
    ffmpeg = _get_ffmpeg()
    duration = get_video_duration(video_path)

    num_frames = min(max_frames, max(1, int(duration)))
    interval = duration / num_frames if num_frames > 1 else duration

    frames = []
    for i in range(num_frames):
        timestamp = i * interval
        frame_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")

        subprocess.run(
            [
                ffmpeg, "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                frame_path,
            ],
            capture_output=True,
            check=False,
        )

        if os.path.isfile(frame_path) and os.path.getsize(frame_path) > 0:
            frames.append({
                "frame_path": frame_path,
                "timestamp": timestamp,
                "frame_index": i,
            })

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
