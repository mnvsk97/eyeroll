"""Tests for new features: model upgrade, whisper filtering, scene detection,
frame chaining, and cost reporting."""

import os
from unittest.mock import MagicMock, patch

import pytest

from eyeroll.backend import GeminiBackend
from eyeroll.cost import estimate_cost, format_cost


# ---------------------------------------------------------------------------
# 1. Model upgrade: default is gemini-2.5-flash
# ---------------------------------------------------------------------------


def test_gemini_default_model_is_2_5_flash():
    """GeminiBackend default model should be gemini-2.5-flash."""
    with patch("eyeroll.backend.GeminiBackend._load_service_account", return_value=(None, None)), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        # Mock the google.genai import
        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
            backend = GeminiBackend()
    assert backend._model == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# 2. Whisper confidence filtering
# ---------------------------------------------------------------------------


def test_whisper_filtering_drops_low_confidence(tmp_path):
    """Low-confidence segments are dropped from transcript."""
    from eyeroll.backend import OpenAIBackend

    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"\x00" * 100)

    seg_high = MagicMock()
    seg_high.avg_logprob = -0.2  # high confidence
    seg_high.text = "Hello world"

    seg_low = MagicMock()
    seg_low.avg_logprob = -3.0  # very low confidence
    seg_low.text = "garbled noise"

    mock_transcript = MagicMock()
    mock_transcript.segments = [seg_high, seg_low]
    mock_transcript.text = "Hello world garbled noise"

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_transcript

    backend = OpenAIBackend.__new__(OpenAIBackend)
    backend._client = mock_client
    backend._model = "gpt-4o"
    backend._has_whisper = True

    result = backend.analyze_audio(str(audio_file), "transcribe", min_confidence=0.4)

    assert "Hello world" in result
    assert "garbled noise" not in result


def test_whisper_filtering_poor_audio_quality_warning(tmp_path):
    """When >50% of segments are low-confidence, adds audio_quality warning."""
    from eyeroll.backend import OpenAIBackend

    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"\x00" * 100)

    seg_good = MagicMock()
    seg_good.avg_logprob = -0.1
    seg_good.text = "Good"

    seg_bad1 = MagicMock()
    seg_bad1.avg_logprob = -5.0
    seg_bad1.text = "Bad1"

    seg_bad2 = MagicMock()
    seg_bad2.avg_logprob = -5.0
    seg_bad2.text = "Bad2"

    mock_transcript = MagicMock()
    mock_transcript.segments = [seg_good, seg_bad1, seg_bad2]

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_transcript

    backend = OpenAIBackend.__new__(OpenAIBackend)
    backend._client = mock_client
    backend._model = "gpt-4o"
    backend._has_whisper = True

    result = backend.analyze_audio(str(audio_file), "transcribe", min_confidence=0.4)

    assert "[audio_quality: poor]" in result
    assert "Good" in result


def test_whisper_no_segments_returns_text(tmp_path):
    """When no segments in response, returns raw text."""
    from eyeroll.backend import OpenAIBackend

    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"\x00" * 100)

    mock_transcript = MagicMock()
    mock_transcript.segments = []
    mock_transcript.text = "Plain transcript text"

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_transcript

    backend = OpenAIBackend.__new__(OpenAIBackend)
    backend._client = mock_client
    backend._model = "gpt-4o"
    backend._has_whisper = True

    result = backend.analyze_audio(str(audio_file), "transcribe")
    assert result == "Plain transcript text"


# ---------------------------------------------------------------------------
# 3. Scene-change detection
# ---------------------------------------------------------------------------


def test_pixel_diff(tmp_path):
    """Scene-change pixel diff: identical=0, black vs white=~255."""
    from PIL import Image
    from eyeroll.extract import _pixel_diff

    # Identical
    img = Image.new("L", (160, 90), color=128)
    (tmp_path / "a.jpg").name  # ensure dir exists
    img.save(a := str(tmp_path / "a.jpg"))
    img.save(b := str(tmp_path / "b.jpg"))
    assert _pixel_diff(a, b) == 0.0

    # Black vs white
    Image.new("L", (160, 90), color=0).save(a)
    Image.new("L", (160, 90), color=255).save(b)
    assert _pixel_diff(a, b) > 200


# ---------------------------------------------------------------------------
# 4. Frame context chaining
# ---------------------------------------------------------------------------


def test_frame_chaining_sequential():
    """Sequential mode: frame 0 has no context, frame 1+ gets previous summary, truncated to 300 chars."""
    from eyeroll.analyze import analyze_frames

    long_analysis = "A" * 500
    mock_backend = MagicMock()
    mock_backend.analyze_image.side_effect = [long_analysis, "Second frame"]

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
        {"frame_path": "/tmp/f1.jpg", "timestamp": 2.0, "frame_index": 1},
    ]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_frames(frames, parallel=1)

    # Frame 0: no previous context
    assert "Previous frame context" not in mock_backend.analyze_image.call_args_list[0][0][1]
    # Frame 1: has previous context, truncated to 300 chars
    prompt1 = mock_backend.analyze_image.call_args_list[1][0][1]
    assert "Previous frame context:" in prompt1
    assert "A" * 300 in prompt1
    assert "A" * 301 not in prompt1


def test_frame_chaining_not_in_parallel():
    """Parallel mode does NOT chain context."""
    from eyeroll.analyze import analyze_frames

    mock_backend = MagicMock()
    mock_backend.analyze_image.return_value = "Analysis"

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
        {"frame_path": "/tmp/f1.jpg", "timestamp": 2.0, "frame_index": 1},
    ]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_frames(frames, parallel=2)

    for c in mock_backend.analyze_image.call_args_list:
        assert "Previous frame context" not in c[0][1]


# ---------------------------------------------------------------------------
# 5. Cost reporting
# ---------------------------------------------------------------------------


def test_cost_estimate_gemini():
    """Cost estimate for Gemini with known frame count."""
    info = estimate_cost(
        backend_label="gemini",
        model="gemini-2.5-flash",
        num_frames=10,
    )
    assert info["cost_usd"] > 0
    assert info["model"] == "gemini-2.5-flash"
    assert info["is_estimate"] is True
    assert info["input_tokens"] > 0
    assert info["output_tokens"] > 0


def test_cost_ollama_always_free():
    """Ollama should always report $0.00."""
    info = estimate_cost(
        backend_label="ollama",
        model="qwen3-vl",
        num_frames=100,
    )
    assert info["cost_usd"] == 0.0
    assert info["is_estimate"] is False


def test_cost_actual_tokens():
    """When actual tokens are provided, use them instead of estimates."""
    info = estimate_cost(
        backend_label="gemini",
        model="gemini-2.5-flash",
        num_frames=5,
        actual_input_tokens=1000,
        actual_output_tokens=500,
    )
    assert info["input_tokens"] == 1000
    assert info["output_tokens"] == 500
    assert info["is_estimate"] is False


def test_cost_format():
    """format_cost produces readable output."""
    info = {
        "input_tokens": 15000,
        "output_tokens": 8000,
        "cost_usd": 0.0071,
        "model": "gemini-2.5-flash",
        "is_estimate": True,
    }
    result = format_cost(info)
    assert "$" in result
    assert "gemini-2.5-flash" in result
    assert "~" in result  # estimate indicator


def test_no_cost_flag_suppresses_output(tmp_image_path):
    """--no-cost should suppress cost reporting."""
    from eyeroll.watch import watch

    mock_backend = MagicMock()
    mock_backend.supports_video = True
    mock_backend.supports_audio = True
    mock_backend.preflight.return_value = {
        "healthy": True, "error": None,
        "capabilities": {"video_upload": True, "batch_frames": False,
                         "audio": True, "max_video_mb": 2000},
    }

    with patch("eyeroll.watch.get_backend", return_value=mock_backend), \
         patch("eyeroll.watch.reset_backend"), \
         patch("eyeroll.watch._cache_load", return_value=None), \
         patch("eyeroll.watch._cache_save"), \
         patch("eyeroll.context.discover_context", return_value=None), \
         patch("eyeroll.watch.analyze_frames", return_value=[
             {"frame_index": 0, "timestamp": 0.0, "analysis": "test"}
         ]), \
         patch("eyeroll.watch.synthesize_report", return_value="## Report"), \
         patch("eyeroll.cost.estimate_cost") as mock_cost:
        watch(tmp_image_path, no_cost=True)

    mock_cost.assert_not_called()
