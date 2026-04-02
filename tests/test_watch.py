"""Tests for the watch orchestrator module."""

import os
import shutil
from unittest.mock import MagicMock, patch, call

import pytest

from eyeroll.watch import watch, _wrap_report, _cache_key, _cache_save, _cache_load


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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
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


# ---------------------------------------------------------------------------
# watch() — codebase context integration
# ---------------------------------------------------------------------------

def test_watch_passes_codebase_context(tmp_image_path):
    """watch() passes codebase_context to synthesize_report."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "test"}
         ]), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report") as mock_sr:
        watch(tmp_image_path, codebase_context="## Project: myapp\n**Stack:** Python")

    assert mock_sr.call_args[1]["codebase_context"] == "## Project: myapp\n**Stack:** Python"


def test_watch_works_without_codebase_context(tmp_image_path):
    """watch() works fine when no codebase context is provided."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "test"}
         ]), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report") as mock_sr:
        result = watch(tmp_image_path)

    assert "# eyeroll:" in result
    assert mock_sr.call_args[1]["codebase_context"] is None


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_key_deterministic(tmp_image_path):
    """Same inputs produce the same cache key."""
    k1 = _cache_key(tmp_image_path, "gemini", None)
    k2 = _cache_key(tmp_image_path, "gemini", None)
    assert k1 == k2


def test_cache_key_differs_by_backend(tmp_image_path):
    k1 = _cache_key(tmp_image_path, "gemini", None)
    k2 = _cache_key(tmp_image_path, "ollama", None)
    assert k1 != k2


def test_cache_key_url():
    """URLs produce a stable key without file I/O."""
    k = _cache_key("https://loom.com/share/abc123", "gemini", None)
    assert len(k) == 16


def test_cache_save_and_load(tmp_path):
    intermediates = {
        "title": "test_video",
        "media_type": "video (00:30)",
        "frame_analyses": [{"frame_index": 0, "timestamp": 0.0, "analysis": "test"}],
        "video_analysis": None,
        "transcript": None,
    }
    with patch("eyeroll.watch.CACHE_DIR", str(tmp_path)):
        _cache_save("testkey", "https://example.com/video", intermediates)
        result = _cache_load("testkey")
    assert result is not None
    assert result["title"] == "test_video"
    assert result["media_type"] == "video (00:30)"
    assert result["frame_analyses"] == [{"frame_index": 0, "timestamp": 0.0, "analysis": "test"}]
    assert result["video_analysis"] is None
    assert result["transcript"] is None
    assert result["source"] == "https://example.com/video"


def test_cache_load_miss(tmp_path):
    with patch("eyeroll.watch.CACHE_DIR", str(tmp_path)):
        assert _cache_load("nonexistent") is None


def test_watch_returns_cached_report(tmp_image_path):
    """When cache hits, watch re-runs synthesis but skips analysis."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    cached_intermediates = {
        "title": "test_image",
        "media_type": "screenshot",
        "frame_analyses": [{"frame_index": 0, "timestamp": 0.0, "analysis": "cached analysis"}],
        "video_analysis": None,
        "transcript": None,
    }

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=cached_intermediates), \
         patch("eyeroll.watch.acquire") as mock_acquire, \
         patch("eyeroll.watch.analyze_frames") as mock_af, \
         patch("eyeroll.watch.synthesize_report", return_value="## Synthesized from cache") as mock_sr:
        result = watch(tmp_image_path, context="some context")

    # Should NOT run acquire or analyze_frames
    mock_acquire.assert_not_called()
    mock_af.assert_not_called()
    # Should run synthesize_report with cached intermediates + current context
    mock_sr.assert_called_once()
    assert mock_sr.call_args[1]["context"] == "some context"
    assert mock_sr.call_args[1]["frame_analyses"] == cached_intermediates["frame_analyses"]
    # Final report should include header + synthesized content
    assert "# eyeroll:" in result
    assert "Synthesized from cache" in result


def test_watch_cache_different_context_different_reports(tmp_image_path):
    """Same cached video with different --context produces different reports."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    cached_intermediates = {
        "title": "test_image",
        "media_type": "screenshot",
        "frame_analyses": [{"frame_index": 0, "timestamp": 0.0, "analysis": "cached analysis"}],
        "video_analysis": None,
        "transcript": None,
    }

    def synth_side_effect(**kwargs):
        ctx = kwargs.get("context") or "none"
        return f"## Report with context: {ctx}"

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=cached_intermediates), \
         patch("eyeroll.watch.synthesize_report", side_effect=synth_side_effect) as mock_sr:
        result1 = watch(tmp_image_path, context="bug in login")

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=cached_intermediates), \
         patch("eyeroll.watch.synthesize_report", side_effect=synth_side_effect) as mock_sr:
        result2 = watch(tmp_image_path, context="feature request for dashboard")

    # Both should use cached intermediates but produce different reports
    assert "bug in login" in result1
    assert "feature request for dashboard" in result2
    assert result1 != result2


def test_watch_no_cache_flag_skips_cache(tmp_image_path):
    """--no-cache forces fresh analysis even if cache exists."""
    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load") as mock_cache_load, \
         patch("eyeroll.watch._cache_save"), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "test"}
         ]), \
         patch("eyeroll.watch.synthesize_report", return_value="## Fresh Report"):
        result = watch(tmp_image_path, no_cache=True)

    mock_cache_load.assert_not_called()
    assert "# eyeroll:" in result
