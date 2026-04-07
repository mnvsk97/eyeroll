"""Shared fixtures for eyeroll tests."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Synthetic fixtures directory
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SYNTHETIC_DIR = FIXTURES_DIR / "synthetic"


def _synthetic(name: str) -> str:
    """Return absolute path to a synthetic fixture, skip if missing."""
    path = SYNTHETIC_DIR / name
    if not path.is_file():
        pytest.skip(f"Synthetic fixture not found: {name}. Run: bash tests/fixtures/generate.sh")
    return str(path)


# ---------------------------------------------------------------------------
# Autouse fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_backend_fixture():
    """Reset the global backend cache after every test."""
    yield
    from eyeroll.backend import reset_backend
    reset_backend()


@pytest.fixture(autouse=True)
def clear_ffmpeg_cache():
    """Clear the lru_cache on _get_ffmpeg between tests."""
    yield
    from eyeroll.extract import _get_ffmpeg
    _get_ffmpeg.cache_clear()


# ---------------------------------------------------------------------------
# Legacy stub fixtures (used by existing unit tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_video_path(tmp_path):
    """Create a temporary .mp4 file."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"\x00" * 1024)
    return str(video_file)


@pytest.fixture
def tmp_image_path(tmp_path):
    """Create a temporary .png file."""
    image_file = tmp_path / "test_image.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return str(image_file)


# ---------------------------------------------------------------------------
# Synthetic video fixtures (real ffmpeg-generated files)
# ---------------------------------------------------------------------------

@pytest.fixture
def mp4_video():
    return _synthetic("standard_10s.mp4")


@pytest.fixture
def webm_video():
    return _synthetic("standard_10s.webm")


@pytest.fixture
def mov_video():
    return _synthetic("standard_10s.mov")


@pytest.fixture
def avi_video():
    return _synthetic("standard_10s.avi")


@pytest.fixture
def mkv_video():
    return _synthetic("standard_10s.mkv")


@pytest.fixture
def short_video():
    return _synthetic("short_2s.mp4")


@pytest.fixture
def short_5s_video():
    return _synthetic("short_5s.mp4")


@pytest.fixture
def long_video():
    return _synthetic("long_150s.mp4")


@pytest.fixture
def video_with_audio():
    return _synthetic("with_audio.mp4")


@pytest.fixture
def silent_video():
    return _synthetic("silent.mp4")


@pytest.fixture
def multi_scene_video():
    return _synthetic("multi_scene.mp4")


# ---------------------------------------------------------------------------
# Synthetic image fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def png_image():
    return _synthetic("screenshot.png")


@pytest.fixture
def jpg_image():
    return _synthetic("screenshot.jpg")


@pytest.fixture
def bmp_image():
    return _synthetic("screenshot.bmp")


@pytest.fixture
def gif_image():
    return _synthetic("screenshot.gif")


@pytest.fixture
def tiff_image():
    return _synthetic("screenshot.tiff")


@pytest.fixture
def image_4k():
    return _synthetic("screenshot_4k.png")


@pytest.fixture
def thumbnail_image():
    return _synthetic("thumbnail.png")


# ---------------------------------------------------------------------------
# Real recording fixtures (committed to repo)
# ---------------------------------------------------------------------------

@pytest.fixture
def bug_recording_mov():
    """Real screen recording: web search tool 401 error bug. 31s, no audio, MOV."""
    path = FIXTURES_DIR / "web_search_tool_401_error.mov"
    if not path.is_file():
        pytest.skip("Real fixture not found: web_search_tool_401_error.mov")
    return str(path)


@pytest.fixture
def bug_recording_mp4():
    """Real screen recording: web search tool 401 error bug. MP4 version."""
    path = FIXTURES_DIR / "web_search_tool_401_error.mp4"
    if not path.is_file():
        pytest.skip("Real fixture not found: web_search_tool_401_error.mp4")
    return str(path)


# ---------------------------------------------------------------------------
# Edge case fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def corrupt_video():
    return _synthetic("corrupt_truncated.mp4")


@pytest.fixture
def empty_video():
    return _synthetic("empty.mp4")


@pytest.fixture
def unsupported_file():
    return _synthetic("unsupported.xyz")
