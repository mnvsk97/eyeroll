# CLAUDE.md

## Project

eyeroll — AI eyes that roll through video footage. Takes video URLs (Loom, YouTube), local video files, or screenshots as input. Supports Gemini Flash (API) and Ollama with Qwen3-VL (local, private). Produces structured notes that coding agents can act on — fix bugs, build features, create skills, or anything else.

## Commands

```bash
# Install
pip install .
# or with uv:
uv sync

# Run tests
pytest
pytest --cov --cov-report=term-missing

# CLI
eyeroll init                                              # set up Gemini API key
eyeroll watch <url-or-path>                               # analyze (gemini default)
eyeroll watch <url> --context "broken after PR #432"      # with context
eyeroll watch <path> --backend ollama                     # use local Qwen3-VL
eyeroll watch <path> -b ollama -m qwen3-vl:2b             # specific model
eyeroll watch <path> --verbose --output report.md         # verbose + write to file
```

## Architecture

- **Pipeline**: `acquire.py` → `extract.py` → `analyze.py` → `watch.py` (orchestrator)
- **backend.py**: Abstract Backend class with GeminiBackend and OllamaBackend implementations. Factory via `get_backend()`.
- **acquire.py**: Downloads from URLs via yt-dlp, resolves local files. Returns file_path, media_type, title.
- **extract.py**: ffmpeg wrappers for key frame extraction, audio extraction, duration detection.
- **analyze.py**: Backend-agnostic analysis. Frame-by-frame with structured prompts, direct video upload (Gemini only), audio transcription, and synthesis.
- **watch.py**: Orchestrates the pipeline. Chooses strategy based on backend capabilities and video size.
- **cli.py**: Click CLI with `init` and `watch` commands. `--backend` and `--model` flags.

## Backends

- **gemini** (default): Gemini Flash API. Supports direct video upload, audio transcription. Requires GEMINI_API_KEY.
- **ollama**: Local models via Ollama. Supports frame-by-frame image analysis only (no direct video, no audio). Default model: qwen3-vl. No API key needed.

## Key design decisions

- **Backend abstraction**: `Backend` ABC with `analyze_image`, `analyze_video`, `analyze_audio`, `generate`. Each backend declares what it supports via `supports_video` / `supports_audio`.
- **Direct upload vs frame-by-frame**: Gemini gets full video when small enough. Ollama always uses frame-by-frame since it only handles images.
- **Ollama auto-pulls models**: If the model isn't installed, the backend pulls it automatically on first use.
- **Context text is critical**: Most videos are silent screen recordings. The surrounding text often contains more intent than the video itself.

## Testing patterns

- Mock all API/Ollama calls in tests — never hit external services.
- Use synthetic test videos generated via ffmpeg fixtures.
- Test acquire.py with both URL and local file paths.
