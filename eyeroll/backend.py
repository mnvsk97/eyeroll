"""Backend abstraction for vision/language model calls.

Supports:
  - gemini: Google Gemini Flash API (requires GEMINI_API_KEY)
  - openai: OpenAI GPT-4o API (requires OPENAI_API_KEY)
  - ollama: Local Ollama with vision models like qwen3-vl (no API key needed)
  - openrouter: OpenRouter API (requires OPENROUTER_API_KEY)
  - groq: Groq API (requires GROQ_API_KEY)
  - grok: xAI Grok API (requires GROK_API_KEY)
  - cerebras: Cerebras API (requires CEREBRAS_API_KEY)
  - openai-compat: Any OpenAI-compatible endpoint (requires base_url + API key)
"""

import base64
import os
import sys
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()

IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
}


class AnalysisError(RuntimeError):
    """Raised when analysis fails."""


class Backend(ABC):
    """Base class for vision/language model backends."""

    @abstractmethod
    def analyze_image(self, image_path: str, prompt: str, verbose: bool = False) -> str:
        """Analyze a single image with a text prompt. Returns text response."""
        ...

    @abstractmethod
    def analyze_video(self, video_path: str, prompt: str, verbose: bool = False) -> str:
        """Analyze a video file with a text prompt. Returns text response."""
        ...

    @abstractmethod
    def analyze_audio(self, audio_path: str, prompt: str, verbose: bool = False) -> str:
        """Analyze/transcribe an audio file. Returns text response."""
        ...

    @abstractmethod
    def generate(self, prompt: str, verbose: bool = False) -> str:
        """Text-only generation (for synthesis). Returns text response."""
        ...

    @property
    @abstractmethod
    def supports_video(self) -> bool:
        """Whether this backend can analyze video files directly."""
        ...

    @property
    @abstractmethod
    def supports_audio(self) -> bool:
        """Whether this backend can process audio files directly."""
        ...


# ---------------------------------------------------------------------------
# Gemini Backend
# ---------------------------------------------------------------------------

class GeminiBackend(Backend):
    """Google Gemini Flash API backend."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "Gemini backend requires google-genai. Install with: pip install eyeroll[gemini]"
            )
        api_key = os.environ.get("GEMINI_API_KEY")
        credentials, project = self._load_service_account()

        if api_key:
            self._client = genai.Client(api_key=api_key)
        elif credentials:
            self._client = genai.Client(
                vertexai=True,
                credentials=credentials,
                project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"),
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
        else:
            raise AnalysisError(
                "No Gemini credentials found.\n\n"
                "Option 1 — API key:\n"
                "  Get a free key at: https://aistudio.google.com/apikey\n"
                "  Then: export GEMINI_API_KEY=your-key\n\n"
                "Option 2 — Service account:\n"
                "  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json\n\n"
                "Option 3 — Local model (no credentials needed):\n"
                "  eyeroll watch <source> --backend ollama"
            )
        self._model = model

    @staticmethod
    def _load_service_account():
        """Try to load Google service account credentials.

        Checks GOOGLE_APPLICATION_CREDENTIALS env var, then common paths.
        Returns (credentials, project_id) or (None, None).
        """
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            # Check common locations
            for candidate in [
                os.path.join(os.path.expanduser("~"), ".eyeroll", "credentials.json"),
                "credentials.json",
            ]:
                if os.path.isfile(candidate):
                    creds_path = candidate
                    break

        if not creds_path or not os.path.isfile(creds_path):
            return None, None

        try:
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            # Extract project ID from the credentials file
            import json
            with open(creds_path) as f:
                project_id = json.load(f).get("project_id")
            return credentials, project_id
        except Exception:
            return None, None

    def analyze_image(self, image_path: str, prompt: str, verbose: bool = False) -> str:
        from google.genai import types
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = IMAGE_MIME_TYPES.get(ext, "image/jpeg")

        response = self._client.models.generate_content(
            model=self._model,
            contents=types.Content(role="user", parts=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                types.Part(text=prompt),
            ]),
        )
        return response.text

    def analyze_video(self, video_path: str, prompt: str, verbose: bool = False) -> str:
        from google.genai import types
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        response = self._client.models.generate_content(
            model=self._model,
            contents=types.Content(role="user", parts=[
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                types.Part(text=prompt),
            ]),
        )
        return response.text

    def analyze_audio(self, audio_path: str, prompt: str, verbose: bool = False) -> str:
        from google.genai import types
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        response = self._client.models.generate_content(
            model=self._model,
            contents=types.Content(role="user", parts=[
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3"),
                types.Part(text=prompt),
            ]),
        )
        return response.text

    def generate(self, prompt: str, verbose: bool = False) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text

    @property
    def supports_video(self) -> bool:
        return True

    @property
    def supports_audio(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# OpenAI Backend (also handles OpenAI-compatible providers)
# ---------------------------------------------------------------------------

# Maps provider name -> (base_url, api_key_env, default_model, has_whisper)
# has_whisper=False: the Whisper transcription endpoint only exists on OpenAI proper.
_OPENAI_COMPAT_PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1",   "OPENROUTER_API_KEY", "openai/gpt-4o",           False),
    "groq":       ("https://api.groq.com/openai/v1", "GROQ_API_KEY",       "llama-3.3-70b-versatile", False),
    "grok":       ("https://api.x.ai/v1",            "GROK_API_KEY",       "grok-2-vision-1212",      False),
    "cerebras":   ("https://api.cerebras.ai/v1",     "CEREBRAS_API_KEY",   "llama3.1-70b",            False),
}


class OpenAIBackend(Backend):
    """OpenAI GPT-4o API backend.

    Also handles OpenAI-compatible providers (Groq, Grok, OpenRouter, Cerebras) and
    custom self-hosted endpoints. Use get_backend() to construct for named providers.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        has_whisper: bool = True,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI backend requires openai. Install with: pip install eyeroll[openai]"
            )
        # Try the provider-specific env var first, then fall back to OPENAI_API_KEY
        api_key = os.environ.get(api_key_env) or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise AnalysisError(
                f"No API key found. Set {api_key_env} and try again.\n\n"
                "Or use a different backend:\n"
                "  eyeroll watch <source> --backend gemini\n"
                "  eyeroll watch <source> --backend ollama"
            )
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._has_whisper = has_whisper  # only OpenAI's endpoint has Whisper

    def analyze_image(self, image_path: str, prompt: str, verbose: bool = False) -> str:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = IMAGE_MIME_TYPES.get(ext, "image/jpeg")

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.choices[0].message.content

    def analyze_video(self, video_path: str, prompt: str, verbose: bool = False) -> str:
        raise AnalysisError(
            "OpenAI-compatible backends do not support direct video upload. "
            "Use frame-by-frame mode instead."
        )

    def analyze_audio(self, audio_path: str, prompt: str, verbose: bool = False) -> str:
        if not self._has_whisper:
            raise AnalysisError(
                f"Audio transcription is not supported for this provider. "
                "Only the OpenAI backend has the Whisper endpoint."
            )
        with open(audio_path, "rb") as f:
            transcript = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return transcript.text

    def generate(self, prompt: str, verbose: bool = False) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    @property
    def supports_video(self) -> bool:
        return False

    @property
    def supports_audio(self) -> bool:
        return self._has_whisper


# ---------------------------------------------------------------------------
# Ollama Backend
# ---------------------------------------------------------------------------

class OllamaBackend(Backend):
    """Local Ollama backend for vision models (qwen3-vl, llava, etc.)."""

    def __init__(self, model: str = "qwen3-vl", host: str | None = None):
        self._model = model
        self._host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self._check_connection()

    def _check_connection(self):
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(f"{self._host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            # Try to install and start Ollama automatically
            if self._try_install_ollama():
                return
            raise AnalysisError(
                f"Cannot connect to Ollama at {self._host}.\n\n"
                "Make sure Ollama is running:\n"
                "  ollama serve\n\n"
                "Install Ollama: https://ollama.com"
            )

    def _try_install_ollama(self) -> bool:
        """Try to install Ollama and start the server. Returns True if successful."""
        import platform
        import shutil
        import subprocess
        import time
        import urllib.request

        # Check if ollama binary exists but server isn't running
        if shutil.which("ollama"):
            print("  Ollama found but not running. Starting ollama serve...", file=sys.stderr)
        else:
            # Install Ollama
            if platform.system() not in ("Darwin", "Linux"):
                return False
            print("  Ollama not found. Installing...", file=sys.stderr)
            try:
                subprocess.run(
                    ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                    check=True, timeout=120,
                )
                print("  Ollama installed.", file=sys.stderr)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                return False

        # Start ollama serve in the background
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Wait for server to be ready
            for _ in range(10):
                time.sleep(1)
                try:
                    req = urllib.request.Request(f"{self._host}/api/tags")
                    with urllib.request.urlopen(req, timeout=3):
                        print("  Ollama is running.", file=sys.stderr)
                        return True
                except Exception:
                    continue
        except FileNotFoundError:
            pass
        return False

    def _check_model(self):
        """Pull the model if not already available."""
        import json
        import urllib.request
        import urllib.error

        req = urllib.request.Request(f"{self._host}/api/tags")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        installed = [m["name"] for m in data.get("models", [])]
        # Check if model (with or without :latest tag) is installed
        if not any(self._model in name for name in installed):
            print(f"  Pulling {self._model} (first time only)...", file=sys.stderr)
            req = urllib.request.Request(
                f"{self._host}/api/pull",
                data=json.dumps({"name": self._model}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                # Stream the response to show progress
                for line in resp:
                    try:
                        status = json.loads(line)
                        if "status" in status:
                            print(f"    {status['status']}", file=sys.stderr, end="\r")
                    except json.JSONDecodeError:
                        pass
                print("", file=sys.stderr)

    def _call(self, prompt: str, images: list[str] | None = None) -> str:
        """Call Ollama generate API.

        Args:
            prompt: text prompt
            images: list of base64-encoded image strings (optional)
        """
        import json
        import urllib.request

        self._check_model()

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images

        req = urllib.request.Request(
            f"{self._host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read())

        return data.get("response", "")

    def analyze_image(self, image_path: str, prompt: str, verbose: bool = False) -> str:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return self._call(prompt, images=[b64])

    def analyze_video(self, video_path: str, prompt: str, verbose: bool = False) -> str:
        # Ollama doesn't support video directly — this should not be called.
        # The orchestrator should use frame-by-frame for Ollama.
        raise AnalysisError(
            "Ollama does not support direct video analysis. "
            "Use frame-by-frame mode instead."
        )

    def analyze_audio(self, audio_path: str, prompt: str, verbose: bool = False) -> str:
        # Ollama doesn't support audio. The orchestrator skips audio for Ollama.
        raise AnalysisError(
            "Ollama does not support audio analysis. "
            "Audio transcription is skipped with the Ollama backend."
        )

    def generate(self, prompt: str, verbose: bool = False) -> str:
        return self._call(prompt)

    @property
    def supports_video(self) -> bool:
        return False

    @property
    def supports_audio(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_current_backend: Backend | None = None


def get_backend(name: str | None = None, **kwargs) -> Backend:
    """Get or create the active backend.

    Args:
        name: Backend name. One of: 'gemini', 'openai', 'ollama', 'openrouter', 'groq',
              'grok', 'cerebras', 'openai-compat'.
              Defaults to EYEROLL_BACKEND env var, then 'gemini'.
        **kwargs: Passed to backend constructor (e.g., model, host, base_url).
    """
    global _current_backend
    if _current_backend is not None:
        return _current_backend

    if name is None:
        name = os.environ.get("EYEROLL_BACKEND", "gemini")

    if name == "gemini":
        _current_backend = GeminiBackend(**kwargs)
    elif name == "openai":
        _current_backend = OpenAIBackend(**kwargs)
    elif name == "ollama":
        _current_backend = OllamaBackend(**kwargs)
    elif name in _OPENAI_COMPAT_PROVIDERS:
        url, key_env, default_model, has_whisper = _OPENAI_COMPAT_PROVIDERS[name]
        _current_backend = OpenAIBackend(
            model=kwargs.get("model", default_model),
            base_url=url,
            api_key_env=key_env,
            has_whisper=has_whisper,
        )
    elif name == "openai-compat":
        # Requires base_url in kwargs; model is optional
        _current_backend = OpenAIBackend(has_whisper=False, **kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {name}. "
            "Use 'gemini', 'openai', 'ollama', 'openrouter', 'groq', 'grok', "
            "'cerebras', or 'openai-compat'."
        )

    return _current_backend


def reset_backend():
    """Reset the cached backend."""
    global _current_backend
    _current_backend = None
