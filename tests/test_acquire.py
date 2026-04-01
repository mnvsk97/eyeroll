"""Basic tests for the acquire module."""

import os
from pathlib import Path

from eyeroll.acquire import detect_media_type, _is_url


def test_detect_video_types():
    assert detect_media_type("video.mp4") == "video"
    assert detect_media_type("video.webm") == "video"
    assert detect_media_type("video.mov") == "video"


def test_detect_image_types():
    assert detect_media_type("screenshot.png") == "image"
    assert detect_media_type("screenshot.jpg") == "image"
    assert detect_media_type("screenshot.gif") == "image"


def test_is_url():
    assert _is_url("https://loom.com/share/abc123")
    assert _is_url("http://example.com/video.mp4")
    assert not _is_url("/path/to/file.mp4")
    assert not _is_url("./relative/file.mp4")
