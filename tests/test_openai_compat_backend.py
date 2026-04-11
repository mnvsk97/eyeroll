"""Tests for OpenAI-compatible provider support in OpenAIBackend."""

import os
from unittest.mock import MagicMock, patch

import pytest

from eyeroll.backend import (
    AnalysisError,
    OpenAIBackend,
    _OPENAI_COMPAT_PROVIDERS,
    get_backend,
    reset_backend,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_openai_compat(provider=None, **kwargs):
    """Create an OpenAIBackend for a known provider, with the OpenAI client mocked."""
    url, key_env, default_model, has_whisper = _OPENAI_COMPAT_PROVIDERS[provider]
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {key_env: "test-key"}):
        return OpenAIBackend(
            model=kwargs.get("model", default_model),
            base_url=url,
            api_key_env=key_env,
            has_whisper=has_whisper,
        )


# ---------------------------------------------------------------------------
# _OPENAI_COMPAT_PROVIDERS preset values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["openrouter", "groq", "grok", "cerebras"])
def test_provider_preset_exists(name):
    assert name in _OPENAI_COMPAT_PROVIDERS


@pytest.mark.parametrize("name", ["openrouter", "groq", "grok", "cerebras"])
def test_provider_has_whisper_false(name):
    """None of the compat providers have the Whisper endpoint."""
    _, _, _, has_whisper = _OPENAI_COMPAT_PROVIDERS[name]
    assert has_whisper is False


def test_gemini_not_in_compat_providers():
    """Gemini is handled by the native GeminiBackend, not the compat layer."""
    assert "gemini" not in _OPENAI_COMPAT_PROVIDERS


# ---------------------------------------------------------------------------
# Constructor — known providers via get_backend()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,key_env", [
    ("openrouter", "OPENROUTER_API_KEY"),
    ("groq",       "GROQ_API_KEY"),
    ("grok",       "GROK_API_KEY"),
    ("cerebras",   "CEREBRAS_API_KEY"),
])
def test_get_backend_known_provider(name, key_env):
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {key_env: "test-key"}):
        backend = get_backend(name)
        assert isinstance(backend, OpenAIBackend)


def test_get_backend_openai_compat_with_base_url():
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        backend = get_backend("openai-compat", base_url="https://custom.server/v1")
        assert isinstance(backend, OpenAIBackend)


def test_get_backend_openai_compat_has_whisper_false():
    """Custom compat endpoints default to has_whisper=False."""
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        backend = get_backend("openai-compat", base_url="https://custom.server/v1")
        assert backend.supports_audio is False


# ---------------------------------------------------------------------------
# Default models
# ---------------------------------------------------------------------------

def test_groq_default_model():
    backend = _make_openai_compat("groq")
    assert backend._model == "llama-3.3-70b-versatile"


def test_openrouter_default_model():
    backend = _make_openai_compat("openrouter")
    assert backend._model == "openai/gpt-4o"


def test_grok_default_model():
    backend = _make_openai_compat("grok")
    assert backend._model == "grok-2-vision-1212"


def test_cerebras_default_model():
    backend = _make_openai_compat("cerebras")
    assert backend._model == "llama3.1-70b"


def test_model_override():
    backend = _make_openai_compat("groq", model="llama3-8b-8192")
    assert backend._model == "llama3-8b-8192"


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------

def test_provider_specific_env_var_used():
    """GROQ_API_KEY is picked up for the groq provider."""
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    env["GROQ_API_KEY"] = "groq-secret"
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        backend = get_backend("groq")
        assert isinstance(backend, OpenAIBackend)


def test_openai_key_fallback_for_provider():
    """OPENAI_API_KEY is used when provider-specific key is absent."""
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    env["OPENAI_API_KEY"] = "fallback-key"
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        backend = get_backend("groq")
        assert isinstance(backend, OpenAIBackend)


def test_missing_api_key_raises():
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        with pytest.raises(AnalysisError, match="No API key found"):
            get_backend("groq")


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["openrouter", "groq", "grok", "cerebras"])
def test_supports_video_is_false(name):
    backend = _make_openai_compat(name)
    assert backend.supports_video is False


@pytest.mark.parametrize("name", ["openrouter", "groq", "grok", "cerebras"])
def test_supports_audio_is_false(name):
    """Compat providers have no Whisper endpoint."""
    backend = _make_openai_compat(name)
    assert backend.supports_audio is False


# ---------------------------------------------------------------------------
# analyze_video raises
# ---------------------------------------------------------------------------

def test_analyze_video_raises(tmp_path):
    backend = _make_openai_compat("groq")
    with pytest.raises(AnalysisError, match="do not support direct video"):
        backend.analyze_video(str(tmp_path / "v.mp4"), "describe")


# ---------------------------------------------------------------------------
# analyze_audio raises for compat providers (no Whisper)
# ---------------------------------------------------------------------------

def test_analyze_audio_raises_for_compat_provider(tmp_video_path):
    backend = _make_openai_compat("groq")
    with pytest.raises(AnalysisError, match="Audio transcription is not supported"):
        backend.analyze_audio(tmp_video_path, "transcribe")


# ---------------------------------------------------------------------------
# analyze_image
# ---------------------------------------------------------------------------

def test_analyze_image_returns_content(tmp_image_path):
    backend = _make_openai_compat("groq")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Image analysis result"))]
    backend._client.chat.completions.create.return_value = mock_response

    result = backend.analyze_image(tmp_image_path, "Describe this")
    assert result == "Image analysis result"
    backend._client.chat.completions.create.assert_called_once()


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

def test_generate_returns_text():
    backend = _make_openai_compat("groq")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated output"))]
    backend._client.chat.completions.create.return_value = mock_response

    result = backend.generate("test prompt")
    assert result == "Generated output"
    backend._client.chat.completions.create.assert_called_once_with(
        model=backend._model,
        messages=[{"role": "user", "content": "test prompt"}],
    )


# ---------------------------------------------------------------------------
# OpenAI proper still has Whisper
# ---------------------------------------------------------------------------

def test_openai_proper_supports_audio():
    """The standard openai backend (has_whisper=True) still works."""
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        backend = OpenAIBackend()
        assert backend.supports_audio is True


def test_openai_proper_analyze_audio(tmp_video_path):
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        backend = OpenAIBackend()
        backend._client.audio.transcriptions.create.return_value = MagicMock(text="Transcript")
        result = backend.analyze_audio(tmp_video_path, "transcribe")
        assert result == "Transcript"
