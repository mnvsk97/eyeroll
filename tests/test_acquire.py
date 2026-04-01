"""Tests for the acquire module."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eyeroll.acquire import (
    acquire,
    detect_media_type,
    _download_url,
    _get_ytdlp,
    _is_url,
    _resolve_local,
)


# ---------------------------------------------------------------------------
# detect_media_type
# ---------------------------------------------------------------------------

def test_detect_video_types():
    assert detect_media_type("video.mp4") == "video"
    assert detect_media_type("video.webm") == "video"
    assert detect_media_type("video.mov") == "video"


def test_detect_image_types():
    assert detect_media_type("screenshot.png") == "image"
    assert detect_media_type("screenshot.jpg") == "image"
    assert detect_media_type("screenshot.gif") == "image"


def test_detect_media_type_unsupported():
    with pytest.raises(ValueError, match="Unsupported file type: .txt"):
        detect_media_type("notes.txt")


def test_detect_media_type_unsupported_pdf():
    with pytest.raises(ValueError, match="Unsupported file type"):
        detect_media_type("document.pdf")


# ---------------------------------------------------------------------------
# _is_url
# ---------------------------------------------------------------------------

def test_is_url():
    assert _is_url("https://loom.com/share/abc123")
    assert _is_url("http://example.com/video.mp4")
    assert not _is_url("/path/to/file.mp4")
    assert not _is_url("./relative/file.mp4")


# ---------------------------------------------------------------------------
# _get_ytdlp
# ---------------------------------------------------------------------------

def test_get_ytdlp_found():
    with patch("eyeroll.acquire.shutil.which", return_value="/usr/local/bin/yt-dlp"):
        assert _get_ytdlp() == "/usr/local/bin/yt-dlp"


def test_get_ytdlp_not_installed():
    with patch("eyeroll.acquire.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="yt-dlp is not installed"):
            _get_ytdlp()


# ---------------------------------------------------------------------------
# _resolve_local
# ---------------------------------------------------------------------------

def test_resolve_local_existing_file(tmp_video_path):
    result = _resolve_local(tmp_video_path)
    assert result["file_path"] == tmp_video_path
    assert result["media_type"] == "video"
    assert result["source_url"] is None
    assert result["title"] == "test_video"


def test_resolve_local_missing_file():
    with pytest.raises(FileNotFoundError, match="File not found"):
        _resolve_local("/nonexistent/path/video.mp4")


def test_resolve_local_image(tmp_image_path):
    result = _resolve_local(tmp_image_path)
    assert result["media_type"] == "image"
    assert result["title"] == "test_image"


# ---------------------------------------------------------------------------
# acquire (dispatcher)
# ---------------------------------------------------------------------------

def test_acquire_local_file(tmp_video_path):
    result = acquire(tmp_video_path)
    assert result["file_path"] == tmp_video_path
    assert result["media_type"] == "video"
    assert result["source_url"] is None


def test_acquire_url():
    meta_json = json.dumps({"title": "My Video"})
    meta_result = MagicMock(returncode=0, stdout=meta_json, stderr="")
    dl_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("eyeroll.acquire.shutil.which", return_value="/usr/local/bin/yt-dlp"), \
         patch("eyeroll.acquire.subprocess.run", side_effect=[meta_result, dl_result]), \
         patch("eyeroll.acquire.tempfile.mkdtemp", return_value="/tmp/eyeroll_test"), \
         patch("eyeroll.acquire._find_media_file", return_value="/tmp/eyeroll_test/My Video.mp4"):
        result = acquire("https://loom.com/share/abc123")
        assert result["source_url"] == "https://loom.com/share/abc123"
        assert result["media_type"] == "video"
        assert result["title"] == "My Video"


# ---------------------------------------------------------------------------
# _download_url
# ---------------------------------------------------------------------------

def test_download_url_success():
    meta_json = json.dumps({"title": "Test Title"})
    meta_result = MagicMock(returncode=0, stdout=meta_json, stderr="")
    dl_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("eyeroll.acquire.shutil.which", return_value="/usr/bin/yt-dlp"), \
         patch("eyeroll.acquire.subprocess.run", side_effect=[meta_result, dl_result]), \
         patch("eyeroll.acquire.tempfile.mkdtemp", return_value="/tmp/eyeroll_test"), \
         patch("eyeroll.acquire._find_media_file", return_value="/tmp/eyeroll_test/Test Title.mp4"):
        result = _download_url("https://example.com/video")
        assert result["title"] == "Test Title"
        assert result["source_url"] == "https://example.com/video"
        assert result["file_path"] == "/tmp/eyeroll_test/Test Title.mp4"


def test_download_url_ytdlp_failure():
    meta_result = MagicMock(returncode=0, stdout="{}", stderr="")
    dl_result = MagicMock(returncode=1, stdout="", stderr="ERROR: unable to download")

    with patch("eyeroll.acquire.shutil.which", return_value="/usr/bin/yt-dlp"), \
         patch("eyeroll.acquire.subprocess.run", side_effect=[meta_result, dl_result]), \
         patch("eyeroll.acquire.tempfile.mkdtemp", return_value="/tmp/eyeroll_test"):
        with pytest.raises(RuntimeError, match="yt-dlp failed to download"):
            _download_url("https://example.com/bad-url")


def test_download_url_no_media_file_found():
    meta_result = MagicMock(returncode=0, stdout="{}", stderr="")
    dl_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("eyeroll.acquire.shutil.which", return_value="/usr/bin/yt-dlp"), \
         patch("eyeroll.acquire.subprocess.run", side_effect=[meta_result, dl_result]), \
         patch("eyeroll.acquire.tempfile.mkdtemp", return_value="/tmp/eyeroll_test"), \
         patch("eyeroll.acquire._find_media_file", return_value=None):
        with pytest.raises(RuntimeError, match="no media file found"):
            _download_url("https://example.com/video")
