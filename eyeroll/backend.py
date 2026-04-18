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


def _logprob_from_confidence(confidence: float) -> float:
    """Convert a 0-1 confidence threshold to a log-probability threshold.

    Whisper segments report avg_logprob (log base e). A confidence of 0.4
    corresponds to ln(0.4) ≈ -0.916.
    """
    import math
    if confidence <= 0:
        return -float("inf")
    return math.log(confidence)


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
    def analyze_audio(
        self, audio_path: str, prompt: str, verbose: bool = False,
        min_confidence: float = 0.4,
    ) -> str:
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

    @property
    def supports_batch_frames(self) -> bool:
        """Whether this backend can analyze multiple frames in one API call."""
        return False

    def analyze_frames_batch(
        self, frame_paths: list[tuple[str, float]], prompt: str, verbose: bool = False,
    ) -> str:
        """Analyze multiple frames in a single API call.

        Args:
            frame_paths: List of (file_path, timestamp_seconds) tuples.
            prompt: Text prompt for the analysis.

        Returns text response combining all frame observations.
        """
        raise NotImplementedError("This backend does not support batch frame analysis.")

    def preflight(self) -> dict:
        """Check backend health and report capabilities.

        Returns dict with:
            healthy: bool
            error: str or None
            capabilities: {video_upload, batch_frames, audio, max_video_mb}
        """
        return {
            "healthy": True,
            "error": None,
            "capabilities": {
                "video_upload": self.supports_video,
                "batch_frames": self.supports_batch_frames,
                "audio": self.supports_audio,
                "max_video_mb": None,
            },
        }


# ---------------------------------------------------------------------------
# Gemini Backend
# ---------------------------------------------------------------------------

class GeminiBackend(Backend):
    """Google Gemini Flash API backend."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "Gemini backend requires google-genai. Install with: pip install eyeroll[gemini]"
            )
        api_key = os.environ.get("GEMINI_API_KEY")
        credentials, project = self._load_service_account()

        self._is_vertex = False
        if api_key:
            self._client = genai.Client(api_key=api_key)
        elif credentials:
            self._is_vertex = True
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
                os.path.join(os.path.expanduser("~"), "credentials.json"),
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
        if self._is_vertex:
            # Vertex AI: inline bytes (File API not supported)
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
        # Developer API: upload via File API (supports up to 2GB)
        file_obj = self._client.files.upload(file=video_path)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=types.Content(role="user", parts=[
                    types.Part.from_uri(file_uri=file_obj.uri, mime_type=file_obj.mime_type or "video/mp4"),
                    types.Part(text=prompt),
                ]),
            )
            return response.text
        finally:
            try:
                self._client.files.delete(name=file_obj.name)
            except Exception:
                pass

    def analyze_audio(
        self, audio_path: str, prompt: str, verbose: bool = False,
        min_confidence: float = 0.4,
    ) -> str:
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

    def preflight(self) -> dict:
        try:
            self._client.models.get(model=self._model)
            # File API (2GB) only on Developer API; Vertex AI uses inline bytes (20MB)
            max_mb = 20 if self._is_vertex else 2000
            return {
                "healthy": True,
                "error": None,
                "capabilities": {
                    "video_upload": True,
                    "batch_frames": False,
                    "audio": True,
                    "max_video_mb": max_mb,
                },
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "capabilities": {
                "video_upload": False, "batch_frames": False, "audio": False, "max_video_mb": None,
            }}


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

    def analyze_audio(
        self, audio_path: str, prompt: str, verbose: bool = False,
        min_confidence: float = 0.4,
    ) -> str:
        if not self._has_whisper:
            raise AnalysisError(
                f"Audio transcription is not supported for this provider. "
                "Only the OpenAI backend has the Whisper endpoint."
            )
        with open(audio_path, "rb") as f:
            transcript = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
            )

        # Filter segments by confidence
        segments = list(getattr(transcript, "segments", None) or [])
        if not segments:
            return getattr(transcript, "text", "") or ""

        kept = [s for s in segments if getattr(s, "avg_logprob", 0.0) >= _logprob_from_confidence(min_confidence)]
        drop_ratio = 1 - (len(kept) / len(segments))

        text = " ".join(getattr(s, "text", "").strip() for s in kept if getattr(s, "text", ""))

        if drop_ratio > 0.5:
            text = f"[audio_quality: poor]\n{text}"

        return text

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

    @property
    def supports_batch_frames(self) -> bool:
        return True

    def analyze_frames_batch(
        self, frame_paths: list[tuple[str, float]], prompt: str, verbose: bool = False,
    ) -> str:
        content = []
        for i, (path, timestamp) in enumerate(frame_paths):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(path)[1].lower()
            mime_type = IMAGE_MIME_TYPES.get(ext, "image/jpeg")
            content.append({"type": "text", "text": f"[Frame {i} @ {timestamp:.1f}s]"})
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}})
        content.append({"type": "text", "text": prompt})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content

    def preflight(self) -> dict:
        try:
            self._client.models.list()
            return {
                "healthy": True,
                "error": None,
                "capabilities": {
                    "video_upload": False,
                    "batch_frames": True,
                    "audio": self._has_whisper,
                    "max_video_mb": None,
                },
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "capabilities": {
                "video_upload": False, "batch_frames": False, "audio": False, "max_video_mb": None,
            }}


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
            with urllib.request.urlopen(req, timeout=5):
                pass
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            raise AnalysisError(
                f"Cannot connect to Ollama at {self._host}. "
                "Start with: ollama serve — Install: https://ollama.com"
            )

    def _check_model(self):
        """Pull the model if not already available."""
        import json
        import urllib.request

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

    def analyze_audio(
        self, audio_path: str, prompt: str, verbose: bool = False,
        min_confidence: float = 0.4,
    ) -> str:
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

    def preflight(self) -> dict:
        import urllib.request
        try:
            req = urllib.request.Request(f"{self._host}/api/tags")
            with urllib.request.urlopen(req, timeout=5):
                pass
            return {
                "healthy": True,
                "error": None,
                "capabilities": {
                    "video_upload": False,
                    "batch_frames": False,
                    "audio": False,
                    "max_video_mb": None,
                },
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "capabilities": {
                "video_upload": False, "batch_frames": False, "audio": False, "max_video_mb": None,
            }}


# ---------------------------------------------------------------------------
# eyeroll hosted API backend
# ---------------------------------------------------------------------------

class EyerollAPIBackend(Backend):
    """Routes analysis requests to the eyeroll hosted API.

    Used automatically when EYEROLL_API_KEY is set in the environment.
    The server handles backend selection and AI calls; the client just
    sends the source URL/path and receives the report.
    """

    def __init__(self):
        self._api_key = os.environ.get("EYEROLL_API_KEY")
        self._api_url = os.environ.get("EYEROLL_API_URL", "https://api.eyeroll.dev").rstrip("/")
        if not self._api_key:
            raise AnalysisError(
                "EYEROLL_API_KEY is not set. "
                "Get a free key at https://api.eyeroll.dev or run `eyeroll init`."
            )

    @property
    def supports_video(self) -> bool:
        return False  # server handles strategy internally

    @property
    def supports_audio(self) -> bool:
        return False

    def analyze_image(self, image_path: str, prompt: str, verbose: bool = False) -> str:
        raise NotImplementedError("Use the watch() pipeline, not analyze_image() directly.")

    def analyze_video(self, video_path: str, prompt: str, verbose: bool = False) -> str:
        raise NotImplementedError("Use the watch() pipeline, not analyze_video() directly.")

    def analyze_audio(self, audio_path: str, prompt: str, verbose: bool = False) -> str:
        raise NotImplementedError("Use the watch() pipeline, not analyze_audio() directly.")

    def generate(self, prompt: str, verbose: bool = False) -> str:
        raise NotImplementedError("Use the watch() pipeline, not generate() directly.")

    def watch(self, source: str, context: str | None = None, max_frames: int = 20) -> str:
        """Send a watch request to the hosted API and return the report.

        Local files are uploaded as multipart form data.
        URLs are sent as JSON.
        """
        import urllib.request
        import json as _json

        is_local = os.path.isfile(source)

        if is_local:
            # Multipart upload for local files
            import mimetypes
            import uuid as _uuid

            boundary = _uuid.uuid4().hex
            filename = os.path.basename(source)
            mime_type = mimetypes.guess_type(source)[0] or "application/octet-stream"

            parts = []
            # File part
            with open(source, "rb") as f:
                file_data = f.read()
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            )
            parts_bytes = parts[0].encode() + file_data + b"\r\n"

            # Text fields
            for field, value in [("context", context), ("max_frames", str(max_frames))]:
                if value is not None:
                    parts_bytes += (
                        f"--{boundary}\r\n"
                        f'Content-Disposition: form-data; name="{field}"\r\n\r\n'
                        f"{value}\r\n"
                    ).encode()

            parts_bytes += f"--{boundary}--\r\n".encode()

            req = urllib.request.Request(
                f"{self._api_url}/api/watch",
                data=parts_bytes,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
        else:
            # JSON for URLs
            payload = _json.dumps({"source": source, "context": context, "max_frames": max_frames}).encode()
            req = urllib.request.Request(
                f"{self._api_url}/api/watch",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = _json.loads(resp.read())
                return data["report"]
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            try:
                detail = _json.loads(body).get("detail", body)
            except Exception:
                detail = body
            raise AnalysisError(f"eyeroll API error {exc.code}: {detail}") from exc

    def preflight(self) -> dict:
        return {
            "healthy": True,
            "error": None,
            "capabilities": {
                "video_upload": False,
                "batch_frames": False,
                "audio": False,
                "max_video_mb": None,
            },
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_current_backend: Backend | None = None


def get_backend(name: str | None = None, **kwargs) -> Backend:
    """Get or create the active backend.

    Args:
        name: Backend name. One of: 'gemini', 'openai', 'ollama', 'openrouter', 'groq',
              'grok', 'cerebras', 'openai-compat', 'eyeroll-api'.
              Defaults to EYEROLL_BACKEND env var, then 'eyeroll-api' if EYEROLL_API_KEY
              is set, otherwise 'gemini'.
        **kwargs: Passed to backend constructor (e.g., model, host, base_url).
    """
    global _current_backend
    if _current_backend is not None:
        return _current_backend

    if name is None:
        name = os.environ.get("EYEROLL_BACKEND")
        if name is None:
            name = "eyeroll-api" if os.environ.get("EYEROLL_API_KEY") else "gemini"

    if name == "gemini":
        _current_backend = GeminiBackend(**kwargs)
    elif name == "openai":
        _current_backend = OpenAIBackend(**kwargs)
    elif name == "ollama":
        _current_backend = OllamaBackend(**kwargs)
    elif name == "eyeroll-api":
        _current_backend = EyerollAPIBackend()
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
            "Use 'gemini', 'openai', 'ollama', 'eyeroll-api', 'openrouter', 'groq', 'grok', "
            "'cerebras', or 'openai-compat'."
        )

    return _current_backend


def reset_backend():
    """Reset the cached backend."""
    global _current_backend
    _current_backend = None
