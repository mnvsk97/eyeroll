"""Tests for the backend module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from eyeroll.backend import (
    AnalysisError,
    GeminiBackend,
    OllamaBackend,
    OpenAIBackend,
    TwelveLabsBackend,
    get_backend,
    reset_backend,
)


# ---------------------------------------------------------------------------
# Helper: create an OllamaBackend without hitting the network
# ---------------------------------------------------------------------------

def _make_ollama(**kwargs):
    """Create an OllamaBackend with the connection check bypassed."""
    with patch.object(OllamaBackend, "_check_connection"):
        return OllamaBackend(**kwargs)


# ---------------------------------------------------------------------------
# get_backend factory
# ---------------------------------------------------------------------------

def test_get_backend_gemini():
    mock_genai = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        backend = get_backend("gemini")
        assert isinstance(backend, GeminiBackend)


def test_get_backend_ollama():
    with patch.object(OllamaBackend, "_check_connection"):
        backend = get_backend("ollama")
        assert isinstance(backend, OllamaBackend)


def test_get_backend_invalid():
    with pytest.raises(ValueError, match="Unknown backend: invalid"):
        get_backend("invalid")


def test_get_backend_twelvelabs():
    mock_twelvelabs_mod = MagicMock()
    with patch.dict(os.environ, {"TWELVE_LABS_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"twelvelabs": mock_twelvelabs_mod}):
        backend = get_backend("twelvelabs")
        assert isinstance(backend, TwelveLabsBackend)


def test_get_backend_caching():
    """Second call to get_backend returns the cached instance."""
    with patch.object(OllamaBackend, "_check_connection"):
        backend1 = get_backend("ollama")
        backend2 = get_backend()  # should return cached
        assert backend1 is backend2


def test_reset_backend():
    """reset_backend clears the cache so a new instance is created."""
    with patch.object(OllamaBackend, "_check_connection"):
        backend1 = get_backend("ollama")
        reset_backend()
        backend2 = get_backend("ollama")
        assert backend1 is not backend2


def test_get_backend_default_gemini():
    """Without args, defaults to gemini."""
    mock_genai = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "EYEROLL_BACKEND"}
    env["GEMINI_API_KEY"] = "test-key"
    with patch.dict(os.environ, env, clear=True), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        backend = get_backend()
        assert isinstance(backend, GeminiBackend)


# ---------------------------------------------------------------------------
# TwelveLabsBackend
# ---------------------------------------------------------------------------

def _make_twelvelabs(**kwargs):
    mock_twelvelabs_mod = MagicMock()
    with patch.dict(os.environ, {"TWELVE_LABS_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"twelvelabs": mock_twelvelabs_mod}):
        return TwelveLabsBackend(**kwargs)


def test_twelvelabs_no_api_key():
    mock_twelvelabs_mod = MagicMock()
    env = {
        k: v for k, v in os.environ.items()
        if k not in {"TWELVE_LABS_API_KEY", "TWELVELABS_API_KEY"}
    }
    with patch.dict(os.environ, env, clear=True), \
         patch.dict("sys.modules", {"twelvelabs": mock_twelvelabs_mod}):
        with pytest.raises(AnalysisError, match="No TwelveLabs API key found"):
            TwelveLabsBackend()


def test_twelvelabs_supports_video_only():
    backend = _make_twelvelabs()

    assert backend.supports_video is True
    assert backend.supports_audio is False
    with pytest.raises(AnalysisError, match="video/audio files"):
        backend.analyze_image("/tmp/screenshot.png", "describe")
    with pytest.raises(AnalysisError, match="text-only synthesis"):
        backend.generate("summarize")


def test_twelvelabs_analyze_video_streams_text(tmp_video_path):
    mock_twelvelabs_mod = MagicMock()
    mock_types_mod = MagicMock()
    mock_types_mod.VideoContext_AssetId.side_effect = lambda asset_id: {"asset_id": asset_id}
    mock_types_mod.AnalyzePromptV2.side_effect = lambda input_text: {"input_text": input_text}

    client = MagicMock()
    client.assets.create.return_value = MagicMock(id="asset-123")
    client.assets.retrieve.return_value = MagicMock(status="ready")
    client.analyze_stream.return_value = [
        MagicMock(event_type="text_generation", text="part one "),
        MagicMock(event_type="text_generation", text="part two"),
    ]
    mock_twelvelabs_mod.TwelveLabs.return_value = client

    with patch.dict(os.environ, {"TWELVE_LABS_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {
             "twelvelabs": mock_twelvelabs_mod,
             "twelvelabs.types": mock_types_mod,
         }):
        backend = TwelveLabsBackend(poll_interval=0)
        result = backend.analyze_video(tmp_video_path, "make report")

    assert result == "part one part two"
    client.assets.create.assert_called_once()
    client.assets.retrieve.assert_called_once_with("asset-123")
    client.analyze_stream.assert_called_once()


# ---------------------------------------------------------------------------
# GeminiBackend
# ---------------------------------------------------------------------------

def test_gemini_backend_no_api_key():
    mock_genai = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        with pytest.raises(AnalysisError, match="No Gemini credentials found"):
            GeminiBackend()


def test_gemini_backend_analyze_image(tmp_image_path):
    mock_genai = MagicMock()
    mock_types = MagicMock()

    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai, "google.genai.types": mock_types}):
        backend = GeminiBackend()
        # Now configure the mock client that was created
        backend._client.models.generate_content.return_value = MagicMock(text="Analysis of the image")
        result = backend.analyze_image(tmp_image_path, "Describe this image")
        assert result == "Analysis of the image"
        backend._client.models.generate_content.assert_called_once()


def test_gemini_supports_video():
    mock_genai = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        backend = GeminiBackend()
        assert backend.supports_video is True


def test_gemini_supports_audio():
    mock_genai = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        backend = GeminiBackend()
        assert backend.supports_audio is True


def test_gemini_generate():
    mock_genai = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        backend = GeminiBackend()
        backend._client.models.generate_content.return_value = MagicMock(text="Generated text")
        result = backend.generate("test prompt")
        assert result == "Generated text"


def test_gemini_analyze_video(tmp_video_path):
    mock_genai = MagicMock()
    mock_types = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai, "google.genai.types": mock_types}):
        backend = GeminiBackend()
        backend._client.models.generate_content.return_value = MagicMock(text="Video result")
        result = backend.analyze_video(tmp_video_path, "Describe video")
        assert result == "Video result"


def test_gemini_analyze_audio(tmp_video_path):
    mock_genai = MagicMock()
    mock_types = MagicMock()
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai, "google.genai.types": mock_types}):
        backend = GeminiBackend()
        backend._client.models.generate_content.return_value = MagicMock(text="Audio result")
        result = backend.analyze_audio(tmp_video_path, "Transcribe")
        assert result == "Audio result"


# ---------------------------------------------------------------------------
# OllamaBackend
# ---------------------------------------------------------------------------

def test_ollama_supports_video():
    backend = _make_ollama()
    assert backend.supports_video is False


def test_ollama_supports_audio():
    backend = _make_ollama()
    assert backend.supports_audio is False


def test_ollama_analyze_video_raises():
    backend = _make_ollama()
    with pytest.raises(AnalysisError, match="does not support direct video"):
        backend.analyze_video("/path/to/video.mp4", "describe")


def test_ollama_analyze_audio_raises():
    backend = _make_ollama()
    with pytest.raises(AnalysisError, match="does not support audio"):
        backend.analyze_audio("/path/to/audio.mp3", "transcribe")


def test_ollama_check_connection_failure():
    import urllib.error
    with patch("urllib.request.urlopen",
               side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(AnalysisError, match="Cannot connect to Ollama"):
            OllamaBackend()


def test_ollama_analyze_image(tmp_image_path):
    """Test that analyze_image reads the file and calls _call."""
    backend = _make_ollama()

    # Mock _call to avoid network
    with patch.object(backend, "_call", return_value="Image analysis"):
        result = backend.analyze_image(tmp_image_path, "Describe this")
        assert result == "Image analysis"
        backend._call.assert_called_once()
        # Verify images list was passed (base64 encoded)
        call_args = backend._call.call_args
        assert call_args[0][0] == "Describe this"
        assert len(call_args[1].get("images", call_args[0][1] if len(call_args[0]) > 1 else [])) == 1


def test_ollama_generate():
    backend = _make_ollama()
    with patch.object(backend, "_call", return_value="Generated response"):
        result = backend.generate("test prompt")
        assert result == "Generated response"


def test_ollama_custom_host():
    backend = _make_ollama(host="http://custom:11434")
    assert backend._host == "http://custom:11434"


def test_ollama_default_model():
    backend = _make_ollama()
    assert backend._model == "qwen3-vl"


def test_ollama_custom_model():
    backend = _make_ollama(model="llava:7b")
    assert backend._model == "llava:7b"


# ---------------------------------------------------------------------------
# OpenAIBackend
# ---------------------------------------------------------------------------

def _make_openai(**kwargs):
    """Create an OpenAIBackend with mocked OpenAI client."""
    mock_openai_mod = MagicMock()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"openai": mock_openai_mod}):
        return OpenAIBackend(**kwargs)


def test_get_backend_openai():
    mock_openai_mod = MagicMock()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), \
         patch.dict("sys.modules", {"openai": mock_openai_mod}):
        backend = get_backend("openai")
        assert isinstance(backend, OpenAIBackend)


def test_openai_no_api_key():
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True), \
         patch.dict("sys.modules", {"openai": mock_openai_mod}):
        with pytest.raises(AnalysisError, match="No API key found"):
            OpenAIBackend()


def test_openai_supports_video():
    backend = _make_openai()
    assert backend.supports_video is False


def test_openai_supports_audio():
    backend = _make_openai()
    assert backend.supports_audio is True


def test_openai_analyze_video_raises():
    backend = _make_openai()
    with pytest.raises(AnalysisError, match="do not support direct video"):
        backend.analyze_video("/path/to/video.mp4", "describe")


def test_openai_analyze_image(tmp_image_path):
    backend = _make_openai()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Image analysis"))]
    backend._client.chat.completions.create.return_value = mock_response

    result = backend.analyze_image(tmp_image_path, "Describe this")
    assert result == "Image analysis"


def test_openai_generate():
    backend = _make_openai()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated text"))]
    backend._client.chat.completions.create.return_value = mock_response

    result = backend.generate("test prompt")
    assert result == "Generated text"


def test_openai_analyze_audio(tmp_video_path):
    backend = _make_openai()
    backend._client.audio.transcriptions.create.return_value = MagicMock(text="Audio transcript")

    result = backend.analyze_audio(tmp_video_path, "Transcribe")
    assert result == "Audio transcript"


def test_openai_default_model():
    backend = _make_openai()
    assert backend._model == "gpt-4o"


def test_openai_custom_model():
    backend = _make_openai(model="gpt-4o-mini")
    assert backend._model == "gpt-4o-mini"
