"""Download or locate video/image from URL or local path."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SUPPORTED_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SUPPORTED_EXTS = SUPPORTED_VIDEO_EXTS | SUPPORTED_IMAGE_EXTS


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _get_ytdlp() -> str:
    path = shutil.which("yt-dlp")
    if path:
        return path
    raise RuntimeError(
        "yt-dlp is not installed.\n\n"
        "Install with: brew install yt-dlp  (macOS)\n"
        "              pip install yt-dlp    (any platform)"
    )


def detect_media_type(file_path: str) -> str:
    """Return 'video' or 'image' based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext in SUPPORTED_VIDEO_EXTS:
        return "video"
    if ext in SUPPORTED_IMAGE_EXTS:
        return "image"
    raise ValueError(f"Unsupported file type: {ext}")


def acquire(source: str, output_dir: str | None = None) -> dict:
    """Download or locate media from a URL or local path.

    Returns dict with keys:
        file_path: absolute path to the media file
        media_type: 'video' or 'image'
        source_url: original URL (or None for local files)
        title: video title (from yt-dlp metadata, or filename)
    """
    if _is_url(source):
        return _download_url(source, output_dir)
    return _resolve_local(source)


def _download_url(url: str, output_dir: str | None = None) -> dict:
    ytdlp = _get_ytdlp()
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="eyeroll_")

    # First, get metadata to know the title
    meta_result = subprocess.run(
        [ytdlp, "--dump-json", "--no-download", url],
        capture_output=True,
        text=True,
        timeout=30,
    )

    title = None
    if meta_result.returncode == 0:
        import json
        try:
            meta = json.loads(meta_result.stdout)
            title = meta.get("title")
        except json.JSONDecodeError:
            pass

    # Download the video
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    result = subprocess.run(
        [
            ytdlp,
            "--no-playlist",
            "--merge-output-format", "mp4",
            "-o", output_template,
            url,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed to download: {url}\n\n"
            f"stderr: {result.stderr[:500]}"
        )

    # Find the downloaded file
    downloaded = _find_media_file(output_dir)
    if not downloaded:
        raise RuntimeError(f"yt-dlp ran successfully but no media file found in {output_dir}")

    return {
        "file_path": downloaded,
        "media_type": detect_media_type(downloaded),
        "source_url": url,
        "title": title or Path(downloaded).stem,
    }


def _resolve_local(path: str) -> dict:
    abs_path = str(Path(path).expanduser().resolve())
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    return {
        "file_path": abs_path,
        "media_type": detect_media_type(abs_path),
        "source_url": None,
        "title": Path(abs_path).stem,
    }


def _find_media_file(directory: str) -> str | None:
    """Find the first supported media file in a directory."""
    for f in sorted(os.listdir(directory)):
        if Path(f).suffix.lower() in SUPPORTED_EXTS:
            return os.path.join(directory, f)
    return None
