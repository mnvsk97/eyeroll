"""Tests for the extract module."""

import json
import os
from unittest.mock import MagicMock, patch, call

import pytest

from eyeroll.extract import (
    _get_ffmpeg,
    extract_audio,
    extract_key_frames,
    fmt_timestamp,
    get_video_duration,
    has_audio_track,
)


# ---------------------------------------------------------------------------
# fmt_timestamp — pure function, no mocks needed
# ---------------------------------------------------------------------------

def test_fmt_timestamp_zero():
    assert fmt_timestamp(0) == "00:00"


def test_fmt_timestamp_seconds():
    assert fmt_timestamp(45) == "00:45"


def test_fmt_timestamp_minutes():
    assert fmt_timestamp(125) == "02:05"


def test_fmt_timestamp_float():
    assert fmt_timestamp(90.7) == "01:30"


def test_fmt_timestamp_large():
    assert fmt_timestamp(3661) == "61:01"


# ---------------------------------------------------------------------------
# _get_ffmpeg
# ---------------------------------------------------------------------------

def test_get_ffmpeg_system():
    with patch("eyeroll.extract.shutil.which", return_value="/usr/local/bin/ffmpeg"):
        assert _get_ffmpeg() == "/usr/local/bin/ffmpeg"


def test_get_ffmpeg_imageio_fallback():
    mock_imageio = MagicMock()
    mock_imageio.get_ffmpeg_exe.return_value = "/path/to/imageio_ffmpeg"

    with patch("eyeroll.extract.shutil.which", return_value=None), \
         patch.dict("sys.modules", {"imageio_ffmpeg": mock_imageio}):
        result = _get_ffmpeg()
        assert result == "/path/to/imageio_ffmpeg"


def test_get_ffmpeg_not_found():
    with patch("eyeroll.extract.shutil.which", return_value=None), \
         patch.dict("sys.modules", {"imageio_ffmpeg": None}):
        # When module is None, import will raise TypeError; but we need to
        # simulate the except branch. Let's use a side_effect on import.
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "imageio_ffmpeg":
                raise ImportError("No module named 'imageio_ffmpeg'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                _get_ffmpeg()


# ---------------------------------------------------------------------------
# get_video_duration
# ---------------------------------------------------------------------------

def test_get_video_duration_ffprobe():
    ffprobe_output = json.dumps({"format": {"duration": "42.5"}})
    mock_result = MagicMock(stdout=ffprobe_output)

    with patch("eyeroll.extract.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result) as mock_run:
        duration = get_video_duration("/path/to/video.mp4")
        assert duration == 42.5
        mock_run.assert_called_once()
        # Verify ffprobe was called with the right args
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/ffprobe"
        assert "/path/to/video.mp4" in args


def test_get_video_duration_ffmpeg_fallback():
    stderr_output = "Duration: 00:01:30.50, start: 0.000000"
    mock_result = MagicMock(stderr=stderr_output)

    with patch("eyeroll.extract.shutil.which", return_value=None), \
         patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result):
        duration = get_video_duration("/path/to/video.mp4")
        assert duration == 90.5


def test_get_video_duration_ffmpeg_no_duration():
    mock_result = MagicMock(stderr="some other output without duration info")

    with patch("eyeroll.extract.shutil.which", return_value=None), \
         patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Could not determine duration"):
            get_video_duration("/path/to/video.mp4")


# ---------------------------------------------------------------------------
# has_audio_track
# ---------------------------------------------------------------------------

def test_has_audio_track_true():
    ffprobe_output = json.dumps({"streams": [{"codec_type": "audio"}]})
    mock_result = MagicMock(returncode=0, stdout=ffprobe_output)

    with patch("eyeroll.extract.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result):
        assert has_audio_track("/path/to/video.mp4") is True


def test_has_audio_track_false_no_streams():
    ffprobe_output = json.dumps({"streams": []})
    mock_result = MagicMock(returncode=0, stdout=ffprobe_output)

    with patch("eyeroll.extract.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result):
        assert has_audio_track("/path/to/video.mp4") is False


def test_has_audio_track_no_ffprobe():
    with patch("eyeroll.extract.shutil.which", return_value=None):
        assert has_audio_track("/path/to/video.mp4") is False


def test_has_audio_track_ffprobe_failure():
    mock_result = MagicMock(returncode=1, stdout="", stderr="error")

    with patch("eyeroll.extract.shutil.which", return_value="/usr/bin/ffprobe"), \
         patch("eyeroll.extract.subprocess.run", return_value=mock_result):
        assert has_audio_track("/path/to/video.mp4") is False


# ---------------------------------------------------------------------------
# extract_key_frames
# ---------------------------------------------------------------------------

def test_extract_key_frames(tmp_path):
    """Test frame extraction with mocked ffmpeg and file creation."""
    output_dir = str(tmp_path / "frames")
    os.makedirs(output_dir)

    def fake_subprocess_run(cmd, **kwargs):
        # Create the output frame file that ffmpeg would produce
        frame_path = cmd[-1]  # last arg is the output path
        if frame_path.endswith(".jpg"):
            with open(frame_path, "wb") as f:
                f.write(b"\xff\xd8\xff" + b"\x00" * 100)  # fake JPEG
        return MagicMock(returncode=0)

    with patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.get_video_duration", return_value=10.0), \
         patch("eyeroll.extract.subprocess.run", side_effect=fake_subprocess_run):
        frames = extract_key_frames(
            "/path/to/video.mp4", max_frames=5, output_dir=output_dir,
            scene_detection=False,
        )
        assert len(frames) == 5
        assert frames[0]["frame_index"] == 0
        assert frames[0]["timestamp"] == 0.0
        assert os.path.basename(frames[0]["frame_path"]) == "frame_000.jpg"
        assert frames[4]["frame_index"] == 4


def test_extract_key_frames_no_output(tmp_path):
    """If ffmpeg doesn't produce files, return empty list."""
    output_dir = str(tmp_path / "frames")
    os.makedirs(output_dir)

    with patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.get_video_duration", return_value=5.0), \
         patch("eyeroll.extract.subprocess.run", return_value=MagicMock(returncode=1)):
        frames = extract_key_frames(
            "/path/to/video.mp4", max_frames=3, output_dir=output_dir,
            scene_detection=False,
        )
        assert frames == []


def test_extract_scene_detection(tmp_path):
    """Scene detection extracts frames at change points."""
    output_dir = str(tmp_path / "frames")
    os.makedirs(output_dir)

    call_count = 0

    def fake_scene_run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        # First call is the scene detection filter
        if call_count == 1:
            # Create scene output files
            for i in range(3):
                fpath = os.path.join(output_dir, f"scene_{i + 1:03d}.jpg")
                with open(fpath, "wb") as f:
                    f.write(b"\xff\xd8\xff" + b"\x00" * 100)
            return MagicMock(
                returncode=0,
                stderr="[showinfo] pts_time:0.5\n[showinfo] pts_time:3.2\n[showinfo] pts_time:7.8\n",
            )
        return MagicMock(returncode=0)

    with patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.subprocess.run", side_effect=fake_scene_run):
        frames = extract_key_frames(
            "/path/to/video.mp4", max_frames=10, output_dir=output_dir,
        )

    assert len(frames) == 3
    assert frames[0]["timestamp"] == 0.5
    assert frames[1]["timestamp"] == 3.2
    assert frames[2]["timestamp"] == 7.8


def test_extract_scene_detection_fallback(tmp_path):
    """Falls back to even-spaced when scene detection finds too few frames."""
    output_dir = str(tmp_path / "frames")
    os.makedirs(output_dir)

    call_count = 0

    def fake_run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        # Scene detection returns nothing (no scenes detected)
        if call_count == 1:
            return MagicMock(returncode=0, stderr="")
        # Even-spaced fallback creates frames
        frame_path = cmd[-1]
        if frame_path.endswith(".jpg"):
            with open(frame_path, "wb") as f:
                f.write(b"\xff\xd8\xff" + b"\x00" * 100)
        return MagicMock(returncode=0)

    with patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.get_video_duration", return_value=10.0), \
         patch("eyeroll.extract.subprocess.run", side_effect=fake_run):
        frames = extract_key_frames(
            "/path/to/video.mp4", max_frames=5, output_dir=output_dir,
        )

    # Should have fallen back to even-spaced
    assert len(frames) >= 3


# ---------------------------------------------------------------------------
# extract_audio
# ---------------------------------------------------------------------------

def test_extract_audio_with_track(tmp_path):
    output_dir = str(tmp_path / "audio")
    os.makedirs(output_dir)

    audio_path = os.path.join(output_dir, "audio.mp3")

    def fake_run(cmd, **kwargs):
        # Create the output audio file
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 2048)  # > 1024 bytes
        return MagicMock(returncode=0)

    with patch("eyeroll.extract.has_audio_track", return_value=True), \
         patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.subprocess.run", side_effect=fake_run):
        result = extract_audio("/path/to/video.mp4", output_dir=output_dir)
        assert result == audio_path


def test_extract_audio_no_audio_track():
    with patch("eyeroll.extract.has_audio_track", return_value=False):
        result = extract_audio("/path/to/video.mp4")
        assert result is None


def test_extract_audio_ffmpeg_failure(tmp_path):
    output_dir = str(tmp_path / "audio")
    os.makedirs(output_dir)

    with patch("eyeroll.extract.has_audio_track", return_value=True), \
         patch("eyeroll.extract._get_ffmpeg", return_value="/usr/bin/ffmpeg"), \
         patch("eyeroll.extract.subprocess.run", return_value=MagicMock(returncode=1)):
        result = extract_audio("/path/to/video.mp4", output_dir=output_dir)
        assert result is None
