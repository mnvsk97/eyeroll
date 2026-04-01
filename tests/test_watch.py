"""Tests for the watch orchestrator module."""

import os
import shutil
from unittest.mock import MagicMock, patch, call

import pytest

from eyeroll.watch import watch, _wrap_report


# ---------------------------------------------------------------------------
# _wrap_report — pure string formatting
# ---------------------------------------------------------------------------

def test_wrap_report_basic():
    result = _wrap_report("Body text", "My Video", "video (01:30)", None, "gemini")
    assert "# eyeroll: My Video" in result
    assert "**Source type:** video (01:30)" in result
    assert "**Backend:** gemini" in result
    assert "Body text" in result
    assert "**Context:**" not in result


def test_wrap_report_with_context():
    result = _wrap_report("Body", "Title", "screenshot", "bug in login", "ollama")
    assert "**Context:** bug in login" in result
    assert "**Backend:** ollama" in result


# ---------------------------------------------------------------------------
# watch() with a local image
# ---------------------------------------------------------------------------

def test_watch_local_image(tmp_image_path):
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True
    mock_backend.analyze_image.return_value = "Image frame analysis"
    mock_backend.generate.return_value = "## Synthesized report"

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "Image frame analysis"}
         ]) as mock_af, \
         patch("eyeroll.watch.synthesize_report", return_value="## Report") as mock_sr:
        result = watch(tmp_image_path, context="check the layout")

    assert "# eyeroll:" in result
    assert "screenshot" in result
    mock_af.assert_called_once()
    mock_sr.assert_called_once()
    # Verify context was passed to synthesize_report
    assert mock_sr.call_args[1]["context"] == "check the layout"


# ---------------------------------------------------------------------------
# watch() with video — direct upload path
# ---------------------------------------------------------------------------

def test_watch_video_direct_upload(tmp_video_path):
    """Small video + backend supports video => direct upload."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.acquire", return_value={
             "file_path": tmp_video_path,
             "media_type": "video",
             "source_url": None,
             "title": "test_video",
         }), \
         patch("eyeroll.watch.get_video_duration", return_value=30.0), \
         patch("eyeroll.watch.os.path.getsize", return_value=5 * 1024 * 1024), \
         patch("eyeroll.watch.analyze_video_direct", return_value="Direct analysis") as mock_direct, \
         patch("eyeroll.watch.has_audio_track", return_value=False), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.watch.fmt_timestamp", return_value="00:30"):
        result = watch(tmp_video_path)

    mock_direct.assert_called_once()
    assert "# eyeroll:" in result


# ---------------------------------------------------------------------------
# watch() with video — frame-by-frame (ollama, no video support)
# ---------------------------------------------------------------------------

def test_watch_video_frame_by_frame(tmp_video_path):
    """Backend does NOT support video => frame-by-frame."""
    mock_backend = MagicMock()
    mock_backend.supports_video = False
    mock_backend.supports_audio = False

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
    ]

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.acquire", return_value={
             "file_path": tmp_video_path,
             "media_type": "video",
             "source_url": None,
             "title": "test_video",
         }), \
         patch("eyeroll.watch.get_video_duration", return_value=30.0), \
         patch("eyeroll.watch.os.path.getsize", return_value=5 * 1024 * 1024), \
         patch("eyeroll.watch.extract_key_frames", return_value=frames) as mock_ekf, \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "frame analysis"}
         ]) as mock_af, \
         patch("eyeroll.watch.has_audio_track", return_value=False), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.watch.fmt_timestamp", return_value="00:30"), \
         patch("eyeroll.watch.shutil.rmtree"):
        result = watch(tmp_video_path)

    mock_ekf.assert_called_once()
    mock_af.assert_called_once()


# ---------------------------------------------------------------------------
# watch() with large video — falls back to frame-by-frame
# ---------------------------------------------------------------------------

def test_watch_large_video_fallback(tmp_video_path):
    """Large video (>20MB) falls back to frame-by-frame even with gemini."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
    ]

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.acquire", return_value={
             "file_path": tmp_video_path,
             "media_type": "video",
             "source_url": None,
             "title": "test_video",
         }), \
         patch("eyeroll.watch.get_video_duration", return_value=60.0), \
         patch("eyeroll.watch.os.path.getsize", return_value=25 * 1024 * 1024), \
         patch("eyeroll.watch.extract_key_frames", return_value=frames) as mock_ekf, \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "frame"}
         ]), \
         patch("eyeroll.watch.has_audio_track", return_value=False), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.watch.fmt_timestamp", return_value="01:00"), \
         patch("eyeroll.watch.shutil.rmtree"):
        result = watch(tmp_video_path)

    # Should use frame-by-frame since file is > 20MB
    mock_ekf.assert_called_once()


def test_watch_long_video_fallback(tmp_video_path):
    """Long video (>120s) falls back to frame-by-frame even with gemini."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
    ]

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.acquire", return_value={
             "file_path": tmp_video_path,
             "media_type": "video",
             "source_url": None,
             "title": "test_video",
         }), \
         patch("eyeroll.watch.get_video_duration", return_value=180.0), \
         patch("eyeroll.watch.os.path.getsize", return_value=10 * 1024 * 1024), \
         patch("eyeroll.watch.extract_key_frames", return_value=frames) as mock_ekf, \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "frame"}
         ]), \
         patch("eyeroll.watch.has_audio_track", return_value=False), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.watch.fmt_timestamp", return_value="03:00"), \
         patch("eyeroll.watch.shutil.rmtree"):
        result = watch(tmp_video_path)

    mock_ekf.assert_called_once()


# ---------------------------------------------------------------------------
# Cleanup of temp files after URL download
# ---------------------------------------------------------------------------

def test_watch_cleans_up_url_download(tmp_path):
    """Temp dir should be cleaned up when source was a URL."""
    tmp_video = tmp_path / "eyeroll_test" / "video.mp4"
    tmp_video.parent.mkdir(parents=True)
    tmp_video.write_bytes(b"\x00" * 1024)

    mock_backend = MagicMock()
    mock_backend.supports_video = False
    mock_backend.supports_audio = False

    frames = [{"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0}]

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch.acquire", return_value={
             "file_path": str(tmp_video),
             "media_type": "video",
             "source_url": "https://example.com/video",
             "title": "video",
         }), \
         patch("eyeroll.watch.get_video_duration", return_value=10.0), \
         patch("eyeroll.watch.os.path.getsize", return_value=1 * 1024 * 1024), \
         patch("eyeroll.watch.extract_key_frames", return_value=frames), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "frame"}
         ]), \
         patch("eyeroll.watch.has_audio_track", return_value=False), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.watch.fmt_timestamp", return_value="00:10"), \
         patch("eyeroll.watch.shutil.rmtree") as mock_rmtree:
        watch("https://example.com/video")

    # rmtree should be called for the parent dir of the downloaded file
    mock_rmtree.assert_any_call(str(tmp_video.parent), ignore_errors=True)
