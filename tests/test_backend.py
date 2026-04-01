"""Tests for the backend module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from eyeroll.backend import (
    AnalysisError,
    GeminiBackend,
    OllamaBackend,
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
# GeminiBackend
# ---------------------------------------------------------------------------

def test_gemini_backend_no_api_key():
    mock_genai = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    with patch.dict(os.environ, env, clear=True), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        with pytest.raises(AnalysisError, match="GEMINI_API_KEY is not set"):
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
