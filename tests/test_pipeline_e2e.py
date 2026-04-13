"""E2E tests for the full watch pipeline using real synthetic fixtures.

These tests run the real acquire + extract pipeline but mock the AI analysis
functions since we don't want to hit external APIs in tests.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from eyeroll.watch import watch


MOCK_FRAME_ANALYSIS = "Frame shows a colored screen with test content."
MOCK_VIDEO_ANALYSIS = "Video shows changing colors over time."
MOCK_AUDIO_TRANSCRIPT = "This is a test recording."
MOCK_SYNTHESIS = "## Video Analysis\n\n### Summary\nTest video with synthetic content."


def _make_frame_result(frames):
    """Build mock frame analysis results matching the real structure."""
    return [
        {"frame_index": i, "timestamp": float(i * 2), "analysis": MOCK_FRAME_ANALYSIS}
        for i in range(len(frames) if isinstance(frames, list) else 1)
    ]


@pytest.fixture(autouse=True)
def disable_cache(tmp_path, monkeypatch):
    """Redirect cache to tmp_path so tests don't pollute the real cache."""
    monkeypatch.setattr("eyeroll.watch.CACHE_DIR", str(tmp_path / "cache"))


def _mock_backend(supports_video=False, supports_audio=False, supports_batch_frames=False):
    backend = MagicMock()
    backend.supports_video = supports_video
    backend.supports_audio = supports_audio
    backend.supports_batch_frames = supports_batch_frames
    backend.preflight.return_value = {
        "healthy": True,
        "error": None,
        "capabilities": {
            "video_upload": supports_video,
            "batch_frames": supports_batch_frames,
            "audio": supports_audio,
            "max_video_mb": 2000 if supports_video else None,
        },
    }
    return backend


# ---------------------------------------------------------------------------
# Video pipeline — frame-by-frame (backend without video support)
# ---------------------------------------------------------------------------

class TestPipelineVideoFrameByFrame:
    def _run(self, video_path, **kwargs):
        backend = _mock_backend(supports_video=False, supports_audio=False)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]) as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(video_path, context="test context", no_cache=True, **kwargs)
        return report, mock_af

    def test_mp4(self, mp4_video):
        report, mock_af = self._run(mp4_video)
        assert "eyeroll:" in report
        assert "test context" in report
        mock_af.assert_called_once()

    def test_webm(self, webm_video):
        report, _ = self._run(webm_video)
        assert "eyeroll:" in report

    def test_mov(self, mov_video):
        report, _ = self._run(mov_video)
        assert "eyeroll:" in report

    def test_avi(self, avi_video):
        report, _ = self._run(avi_video)
        assert "eyeroll:" in report

    def test_mkv(self, mkv_video):
        report, _ = self._run(mkv_video)
        assert "eyeroll:" in report

    def test_short_video(self, short_video):
        report, mock_af = self._run(short_video)
        assert "eyeroll:" in report
        mock_af.assert_called_once()

    def test_multi_scene(self, multi_scene_video):
        report, mock_af = self._run(multi_scene_video)
        assert "eyeroll:" in report
        mock_af.assert_called_once()


# ---------------------------------------------------------------------------
# Video pipeline — direct upload (backend with video support)
# ---------------------------------------------------------------------------

class TestPipelineVideoDirectUpload:
    def test_small_video_uses_direct(self, mp4_video):
        """10s video under 20MB should use direct upload when supported."""
        backend = _mock_backend(supports_video=True, supports_audio=False)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_video_direct", return_value=MOCK_VIDEO_ANALYSIS) as mock_avd, \
             patch("eyeroll.watch.analyze_frames") as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(mp4_video, no_cache=True)
        assert "eyeroll:" in report
        mock_avd.assert_called_once()
        mock_af.assert_not_called()

    def test_long_video_uses_direct_upload(self, long_video):
        """150s video is within the 3600s limit, should use direct upload."""
        backend = _mock_backend(supports_video=True, supports_audio=False)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_video_direct", return_value=MOCK_VIDEO_ANALYSIS) as mock_avd, \
             patch("eyeroll.watch.analyze_frames") as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(long_video, no_cache=True)
        assert "eyeroll:" in report
        mock_avd.assert_called_once()
        mock_af.assert_not_called()


# ---------------------------------------------------------------------------
# Audio pipeline
# ---------------------------------------------------------------------------

class TestPipelineAudio:
    def test_video_with_audio_transcribes(self, video_with_audio):
        backend = _mock_backend(supports_video=False, supports_audio=True)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.analyze_audio", return_value=MOCK_AUDIO_TRANSCRIPT) as mock_aa, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(video_with_audio, no_cache=True)
        assert "eyeroll:" in report
        mock_aa.assert_called_once()

    def test_silent_video_skips_audio(self, silent_video):
        backend = _mock_backend(supports_video=False, supports_audio=True)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.analyze_audio") as mock_aa, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(silent_video, no_cache=True)
        assert "eyeroll:" in report
        mock_aa.assert_not_called()

    def test_backend_without_audio_skips(self, video_with_audio):
        backend = _mock_backend(supports_video=False, supports_audio=False)
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.analyze_audio") as mock_aa, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(video_with_audio, no_cache=True)
        mock_aa.assert_not_called()


# ---------------------------------------------------------------------------
# Image pipeline
# ---------------------------------------------------------------------------

class TestPipelineImage:
    def test_png_screenshot(self, png_image):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]) as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(png_image, no_cache=True)
        assert "eyeroll:" in report
        assert "screenshot" in report.lower()
        mock_af.assert_called_once()

    def test_jpg_screenshot(self, jpg_image):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(jpg_image, no_cache=True)
        assert "eyeroll:" in report

    def test_4k_image(self, image_4k):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(image_4k, no_cache=True)
        assert "eyeroll:" in report

    def test_thumbnail(self, thumbnail_image):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(thumbnail_image, no_cache=True)
        assert "eyeroll:" in report


# ---------------------------------------------------------------------------
# Context and metadata
# ---------------------------------------------------------------------------

class TestPipelineMetadata:
    def test_context_appears_in_report(self, mp4_video):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(mp4_video, context="broken after PR #432", no_cache=True)
        assert "broken after PR #432" in report

    def test_verbose_mode(self, mp4_video, capsys):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            watch(mp4_video, verbose=True, no_cache=True)
        captured = capsys.readouterr()
        assert "Duration" in captured.err or "Strategy" in captured.err

    def test_report_contains_title(self, mp4_video):
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_FRAME_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(mp4_video, no_cache=True)
        assert "standard_10s" in report


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestPipelineEdgeCases:
    def test_corrupt_video(self, corrupt_video):
        """Corrupt video should fail gracefully at duration detection."""
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"):
            with pytest.raises(Exception):
                watch(corrupt_video, no_cache=True)

    def test_empty_video(self, empty_video):
        """Empty video file should fail gracefully."""
        backend = _mock_backend()
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"):
            with pytest.raises(Exception):
                watch(empty_video, no_cache=True)
