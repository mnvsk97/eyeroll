"""Tests using real screen recordings committed to the repo.

These test the full acquire + extract pipeline on actual recordings
(not synthetic ffmpeg-generated fixtures). AI analysis is still mocked.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from eyeroll.acquire import acquire, detect_media_type
from eyeroll.extract import (
    extract_audio,
    extract_key_frames,
    get_video_duration,
    has_audio_track,
)
from eyeroll.watch import watch


# ---------------------------------------------------------------------------
# web_search_tool_401_error — MOV and MP4 versions
# Bug screen recording, ~31s, no audio, shows 401 error in browser
# ---------------------------------------------------------------------------

class TestBugRecordingAcquire:
    def test_mov_detected_as_video(self, bug_recording_mov):
        assert detect_media_type(bug_recording_mov) == "video"

    def test_mp4_detected_as_video(self, bug_recording_mp4):
        assert detect_media_type(bug_recording_mp4) == "video"

    def test_acquire_mov(self, bug_recording_mov):
        result = acquire(bug_recording_mov)
        assert result["media_type"] == "video"
        assert result["source_url"] is None
        assert "web_search_tool_401_error" in result["title"]

    def test_acquire_mp4(self, bug_recording_mp4):
        result = acquire(bug_recording_mp4)
        assert result["media_type"] == "video"


class TestBugRecordingExtract:
    def test_mov_duration(self, bug_recording_mov):
        duration = get_video_duration(bug_recording_mov)
        assert 25.0 <= duration <= 40.0

    def test_mp4_duration(self, bug_recording_mp4):
        duration = get_video_duration(bug_recording_mp4)
        assert 25.0 <= duration <= 40.0

    def test_mov_no_audio(self, bug_recording_mov):
        assert has_audio_track(bug_recording_mov) is False

    def test_mov_frame_extraction(self, bug_recording_mov, tmp_path):
        frames = extract_key_frames(bug_recording_mov, output_dir=str(tmp_path))
        assert len(frames) >= 3
        for f in frames:
            assert os.path.isfile(f["frame_path"])
            # Real screen recordings produce substantial JPEG frames
            assert os.path.getsize(f["frame_path"]) > 10_000

    def test_mp4_frame_extraction(self, bug_recording_mp4, tmp_path):
        frames = extract_key_frames(bug_recording_mp4, output_dir=str(tmp_path))
        assert len(frames) >= 3

    def test_mov_frames_are_different(self, bug_recording_mov, tmp_path):
        """Real recording frames should have variety (not all identical)."""
        frames = extract_key_frames(bug_recording_mov, output_dir=str(tmp_path))
        sizes = [os.path.getsize(f["frame_path"]) for f in frames]
        # At least some frames should differ significantly in size
        size_range = max(sizes) - min(sizes)
        assert size_range > 5000

    def test_mov_no_audio_extraction(self, bug_recording_mov, tmp_path):
        result = extract_audio(bug_recording_mov, output_dir=str(tmp_path))
        assert result is None


MOCK_ANALYSIS = "Frame shows a browser with 401 error."
MOCK_SYNTHESIS = "## Video Analysis\n\n### Summary\nBug recording showing 401 error."


class TestBugRecordingPipeline:
    def test_mov_full_pipeline(self, bug_recording_mov, tmp_path, monkeypatch):
        monkeypatch.setattr("eyeroll.watch.CACHE_DIR", str(tmp_path / "cache"))
        backend = MagicMock()
        backend.supports_video = False
        backend.supports_audio = False
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_ANALYSIS}
             ]) as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(
                bug_recording_mov,
                context="Web search tool returning 401 after deploy",
                no_cache=True,
            )
        assert "eyeroll:" in report
        assert "web_search_tool_401_error" in report
        assert "Web search tool returning 401" in report
        mock_af.assert_called_once()

    def test_mp4_full_pipeline(self, bug_recording_mp4, tmp_path, monkeypatch):
        monkeypatch.setattr("eyeroll.watch.CACHE_DIR", str(tmp_path / "cache"))
        backend = MagicMock()
        backend.supports_video = False
        backend.supports_audio = False
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_frames", return_value=[
                 {"frame_index": 0, "timestamp": 0.0, "analysis": MOCK_ANALYSIS}
             ]), \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(bug_recording_mp4, no_cache=True)
        assert "eyeroll:" in report

    def test_mov_with_direct_upload_backend(self, bug_recording_mov, tmp_path, monkeypatch):
        """31s video < 120s and < 20MB — should use direct upload if supported."""
        monkeypatch.setattr("eyeroll.watch.CACHE_DIR", str(tmp_path / "cache"))
        backend = MagicMock()
        backend.supports_video = True
        backend.supports_audio = False
        with patch("eyeroll.watch.get_backend", return_value=backend), \
             patch("eyeroll.watch.reset_backend"), \
             patch("eyeroll.watch.analyze_video_direct", return_value="Direct analysis") as mock_avd, \
             patch("eyeroll.watch.analyze_frames") as mock_af, \
             patch("eyeroll.watch.synthesize_report", return_value=MOCK_SYNTHESIS):
            report = watch(bug_recording_mov, no_cache=True)
        mock_avd.assert_called_once()
        mock_af.assert_not_called()
