"""E2E tests for the extract module using real synthetic fixtures.

These tests call real ffmpeg — no mocks. They verify that frame extraction,
audio detection, and duration parsing work correctly on actual video files.
"""

import os

import pytest

from eyeroll.extract import (
    extract_audio,
    extract_key_frames,
    get_video_duration,
    has_audio_track,
)


# ---------------------------------------------------------------------------
# get_video_duration — real ffprobe/ffmpeg on real files
# ---------------------------------------------------------------------------

class TestDurationReal:
    def test_10s_video(self, mp4_video):
        duration = get_video_duration(mp4_video)
        assert 9.0 <= duration <= 11.0

    def test_2s_video(self, short_video):
        duration = get_video_duration(short_video)
        assert 1.5 <= duration <= 2.5

    def test_5s_video(self, short_5s_video):
        duration = get_video_duration(short_5s_video)
        assert 4.5 <= duration <= 5.5

    def test_150s_video(self, long_video):
        duration = get_video_duration(long_video)
        assert 148.0 <= duration <= 152.0

    def test_webm_duration(self, webm_video):
        duration = get_video_duration(webm_video)
        assert 9.0 <= duration <= 11.0

    def test_mov_duration(self, mov_video):
        duration = get_video_duration(mov_video)
        assert 9.0 <= duration <= 11.0

    def test_avi_duration(self, avi_video):
        duration = get_video_duration(avi_video)
        assert 9.0 <= duration <= 11.0

    def test_mkv_duration(self, mkv_video):
        duration = get_video_duration(mkv_video)
        assert 9.0 <= duration <= 11.0

    def test_corrupt_video_raises(self, corrupt_video):
        with pytest.raises(Exception):
            get_video_duration(corrupt_video)

    def test_empty_video_raises(self, empty_video):
        with pytest.raises(Exception):
            get_video_duration(empty_video)


# ---------------------------------------------------------------------------
# has_audio_track — real ffprobe detection
# ---------------------------------------------------------------------------

class TestAudioDetectionReal:
    def test_video_with_audio(self, video_with_audio):
        assert has_audio_track(video_with_audio) is True

    def test_silent_video(self, silent_video):
        assert has_audio_track(silent_video) is False

    def test_standard_video_no_audio(self, mp4_video):
        # Our standard synthetic videos are generated without audio
        assert has_audio_track(mp4_video) is False


# ---------------------------------------------------------------------------
# extract_key_frames — real frame extraction
# ---------------------------------------------------------------------------

class TestFrameExtractionReal:
    def test_10s_video_produces_frames(self, mp4_video, tmp_path):
        frames = extract_key_frames(mp4_video, output_dir=str(tmp_path))
        assert len(frames) >= 1
        for f in frames:
            assert os.path.isfile(f["frame_path"])
            assert f["frame_path"].endswith(".jpg")
            assert os.path.getsize(f["frame_path"]) > 0
            assert f["timestamp"] >= 0
            assert f["frame_index"] >= 0

    def test_short_video_few_frames(self, short_video, tmp_path):
        """2s video should yield very few frames."""
        frames = extract_key_frames(short_video, output_dir=str(tmp_path))
        assert 1 <= len(frames) <= 3

    def test_long_video_respects_max_frames(self, long_video, tmp_path):
        """150s video with max_frames=10 should cap at 10."""
        frames = extract_key_frames(long_video, max_frames=10, output_dir=str(tmp_path))
        assert len(frames) <= 10
        assert len(frames) >= 1

    def test_multi_scene_produces_multiple_frames(self, multi_scene_video, tmp_path):
        """Video with distinct color scenes should survive dedup."""
        frames = extract_key_frames(multi_scene_video, output_dir=str(tmp_path))
        # 20s video with hue changes — at minimum first + last kept
        assert len(frames) >= 2

    def test_frame_timestamps_are_ordered(self, mp4_video, tmp_path):
        frames = extract_key_frames(mp4_video, output_dir=str(tmp_path))
        timestamps = [f["timestamp"] for f in frames]
        assert timestamps == sorted(timestamps)

    def test_frame_indices_are_sequential(self, mp4_video, tmp_path):
        frames = extract_key_frames(mp4_video, output_dir=str(tmp_path))
        indices = [f["frame_index"] for f in frames]
        assert indices == list(range(len(frames)))

    def test_webm_frame_extraction(self, webm_video, tmp_path):
        frames = extract_key_frames(webm_video, output_dir=str(tmp_path))
        assert len(frames) >= 1
        assert os.path.isfile(frames[0]["frame_path"])

    def test_mov_frame_extraction(self, mov_video, tmp_path):
        frames = extract_key_frames(mov_video, output_dir=str(tmp_path))
        assert len(frames) >= 1

    def test_avi_frame_extraction(self, avi_video, tmp_path):
        frames = extract_key_frames(avi_video, output_dir=str(tmp_path))
        assert len(frames) >= 1

    def test_mkv_frame_extraction(self, mkv_video, tmp_path):
        frames = extract_key_frames(mkv_video, output_dir=str(tmp_path))
        assert len(frames) >= 1

    def test_enhance_off_still_produces_frames(self, mp4_video, tmp_path):
        frames = extract_key_frames(mp4_video, output_dir=str(tmp_path), enhance=False)
        assert len(frames) >= 1

    def test_corrupt_video_raises(self, corrupt_video, tmp_path):
        """Corrupt video fails at duration detection (ffprobe check=True)."""
        with pytest.raises(Exception):
            extract_key_frames(corrupt_video, output_dir=str(tmp_path))

    def test_empty_video_raises(self, empty_video, tmp_path):
        """Empty file fails at duration detection."""
        with pytest.raises(Exception):
            extract_key_frames(empty_video, output_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# extract_audio — real audio extraction
# ---------------------------------------------------------------------------

class TestAudioExtractionReal:
    def test_extract_audio_from_video_with_audio(self, video_with_audio, tmp_path):
        audio_path = extract_audio(video_with_audio, output_dir=str(tmp_path))
        assert audio_path is not None
        assert os.path.isfile(audio_path)
        assert audio_path.endswith(".mp3")
        assert os.path.getsize(audio_path) > 1024

    def test_extract_audio_from_silent_video(self, silent_video, tmp_path):
        audio_path = extract_audio(silent_video, output_dir=str(tmp_path))
        assert audio_path is None

    def test_extract_audio_from_standard_video(self, mp4_video, tmp_path):
        """Standard synthetic videos have no audio track."""
        audio_path = extract_audio(mp4_video, output_dir=str(tmp_path))
        assert audio_path is None
