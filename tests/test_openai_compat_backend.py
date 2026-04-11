"""Tests for OpenAICompatibleBackend and GeminiServiceAccountBackend."""

import os
from unittest.mock import MagicMock, patch, mock_open

import pytest

from eyeroll.backend import (
    AnalysisError,
    GeminiServiceAccountBackend,
    OpenAICompatibleBackend,
    get_backend,
    reset_backend,
)


# ---------------------------------------------------------------------------
# Helper: create an OpenAICompatibleBackend without hitting any API
# ---------------------------------------------------------------------------

def _make_compat(provider=None, base_url=None, api_key="test-key", model=None):
    """Create an OpenAICompatibleBackend with a mocked OpenAI client."""
    mock_openai_mod = MagicMock()
    env = {"OPENAI_API_KEY": api_key}
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env):
        kwargs = {}
        if provider is not None:
            kwargs["provider"] = provider
        if base_url is not None:
            kwargs["base_url"] = base_url
        if model is not None:
            kwargs["model"] = model
        return OpenAICompatibleBackend(api_key=api_key, **kwargs)


# ---------------------------------------------------------------------------
# Constructor — known provider
# ---------------------------------------------------------------------------

def test_known_provider_groq():
    backend = _make_compat(provider="groq")
    assert backend._model == "llama-3.3-70b-versatile"


def test_known_provider_openrouter():
    backend = _make_compat(provider="openrouter")
    assert backend._model == "openai/gpt-4o"


def test_known_provider_grok():
    backend = _make_compat(provider="grok")
    assert backend._model == "grok-2-vision-1212"


def test_known_provider_cerebras():
    backend = _make_compat(provider="cerebras")
    assert backend._model == "llama3.1-70b"


def test_known_provider_openai():
    backend = _make_compat(provider="openai")
    assert backend._model == "gpt-4o"


def test_known_provider_gemini():
    backend = _make_compat(provider="gemini")
    assert backend._model == "gemini-2.0-flash"


def test_model_override_for_known_provider():
    backend = _make_compat(provider="groq", model="llama3-8b-8192")
    assert backend._model == "llama3-8b-8192"


# ---------------------------------------------------------------------------
# Constructor — custom base_url
# ---------------------------------------------------------------------------

def test_custom_base_url():
    backend = _make_compat(base_url="https://my-server/v1", model="my-model")
    assert backend._model == "my-model"


def test_custom_base_url_default_model():
    """Falls back to gpt-4o when no model is specified for a custom URL."""
    backend = _make_compat(base_url="https://my-server/v1")
    assert backend._model == "gpt-4o"


# ---------------------------------------------------------------------------
# Constructor — error cases
# ---------------------------------------------------------------------------

def test_unknown_provider_raises():
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}):
        with pytest.raises(ValueError, match="Unknown provider: 'notreal'"):
            OpenAICompatibleBackend(provider="notreal", api_key="k")


def test_missing_base_url_and_provider_raises():
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}):
        with pytest.raises(ValueError, match="Either provider= or base_url= must be supplied"):
            OpenAICompatibleBackend(api_key="k")


def test_missing_api_key_raises():
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        with pytest.raises(AnalysisError, match="No API key found"):
            OpenAICompatibleBackend(provider="groq")


def test_provider_specific_env_var_used(monkeypatch):
    """GROQ_API_KEY is picked up automatically for the groq provider."""
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    env["GROQ_API_KEY"] = "groq-secret"
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        # Should not raise — GROQ_API_KEY is present
        backend = OpenAICompatibleBackend(provider="groq")
        assert backend._model == "llama-3.3-70b-versatile"


def test_openai_key_fallback_for_provider(monkeypatch):
    """OPENAI_API_KEY is used as fallback when provider-specific key is absent."""
    mock_openai_mod = MagicMock()
    env = {k: v for k, v in os.environ.items() if k not in ("GROQ_API_KEY", "OPENAI_API_KEY")}
    env["OPENAI_API_KEY"] = "fallback-key"
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, env, clear=True):
        backend = OpenAICompatibleBackend(provider="groq")
        assert backend._model == "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------

def test_supports_video_is_false():
    backend = _make_compat(provider="groq")
    assert backend.supports_video is False


def test_supports_audio_is_true():
    backend = _make_compat(provider="groq")
    assert backend.supports_audio is True


# ---------------------------------------------------------------------------
# analyze_video raises AnalysisError
# ---------------------------------------------------------------------------

def test_analyze_video_raises(tmp_path):
    backend = _make_compat(provider="groq")
    with pytest.raises(AnalysisError, match="does not support direct video"):
        backend.analyze_video(str(tmp_path / "v.mp4"), "describe")


# ---------------------------------------------------------------------------
# analyze_image
# ---------------------------------------------------------------------------

def test_analyze_image_returns_content(tmp_image_path):
    backend = _make_compat(provider="groq")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Image analysis result"))]
    backend._client.chat.completions.create.return_value = mock_response

    result = backend.analyze_image(tmp_image_path, "Describe this")
    assert result == "Image analysis result"
    backend._client.chat.completions.create.assert_called_once()


# ---------------------------------------------------------------------------
# analyze_audio
# ---------------------------------------------------------------------------

def test_analyze_audio_returns_transcript(tmp_video_path):
    backend = _make_compat(provider="groq")
    backend._client.audio.transcriptions.create.return_value = MagicMock(text="Audio transcript")

    result = backend.analyze_audio(tmp_video_path, "Transcribe")
    assert result == "Audio transcript"


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

def test_generate_returns_text():
    backend = _make_compat(provider="groq")
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
# get_backend() factory wiring
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,key_env", [
    ("openrouter", "OPENROUTER_API_KEY"),
    ("groq",       "GROQ_API_KEY"),
    ("grok",       "GROK_API_KEY"),
    ("cerebras",   "CEREBRAS_API_KEY"),
])
def test_get_backend_factory_known_providers(name, key_env):
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {key_env: "test-key"}):
        backend = get_backend(name)
        assert isinstance(backend, OpenAICompatibleBackend)


def test_get_backend_openai_compat_with_base_url():
    mock_openai_mod = MagicMock()
    with patch.dict("sys.modules", {"openai": mock_openai_mod}), \
         patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        backend = get_backend("openai-compat", base_url="https://custom.server/v1")
        assert isinstance(backend, OpenAICompatibleBackend)


# ---------------------------------------------------------------------------
# GeminiServiceAccountBackend
# ---------------------------------------------------------------------------

def _make_gemini_sa(tmp_path):
    """Create a GeminiServiceAccountBackend with all external calls mocked."""
    # Write a minimal fake credentials JSON (structure doesn't matter — SA loading is mocked)
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"type": "service_account"}')

    mock_sa = MagicMock()
    mock_creds = MagicMock()
    mock_creds.token = "fake-bearer-token"
    mock_sa.Credentials.from_service_account_file.return_value = mock_creds

    mock_openai_mod = MagicMock()

    with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.oauth2": MagicMock(),
            "google.oauth2.service_account": mock_sa,
            "google.auth": MagicMock(),
            "google.auth.transport": MagicMock(),
            "google.auth.transport.requests": MagicMock(),
            "openai": mock_openai_mod,
        }):
        backend = GeminiServiceAccountBackend(credentials_path=str(creds_file))

    return backend


def test_gemini_sa_is_backend_instance(tmp_path):
    from eyeroll.backend import Backend
    backend = _make_gemini_sa(tmp_path)
    assert isinstance(backend, Backend)


def test_gemini_sa_supports_video_false(tmp_path):
    backend = _make_gemini_sa(tmp_path)
    assert backend.supports_video is False


def test_gemini_sa_supports_audio_true(tmp_path):
    backend = _make_gemini_sa(tmp_path)
    assert backend.supports_audio is True


def test_gemini_sa_missing_credentials_raises():
    mock_sa = MagicMock()
    with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.oauth2": MagicMock(),
            "google.oauth2.service_account": mock_sa,
            "google.auth": MagicMock(),
            "google.auth.transport": MagicMock(),
            "google.auth.transport.requests": MagicMock(),
        }), \
         patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                  if k != "GOOGLE_APPLICATION_CREDENTIALS"}, clear=True):
        with pytest.raises(AnalysisError, match="No service account credentials found"):
            GeminiServiceAccountBackend(credentials_path="/nonexistent/creds.json")


def test_get_backend_gemini_sa(tmp_path):
    """get_backend('gemini-sa') returns a GeminiServiceAccountBackend."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"type": "service_account"}')

    mock_sa = MagicMock()
    mock_creds = MagicMock()
    mock_creds.token = "fake-token"
    mock_sa.Credentials.from_service_account_file.return_value = mock_creds
    mock_openai_mod = MagicMock()

    with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.oauth2": MagicMock(),
            "google.oauth2.service_account": mock_sa,
            "google.auth": MagicMock(),
            "google.auth.transport": MagicMock(),
            "google.auth.transport.requests": MagicMock(),
            "openai": mock_openai_mod,
        }):
        backend = get_backend("gemini-sa", credentials_path=str(creds_file))
        assert isinstance(backend, GeminiServiceAccountBackend)
