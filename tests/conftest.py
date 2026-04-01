"""Shared fixtures for eyeroll tests."""

import os
import tempfile

import pytest


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
