# Backends

eyeroll supports three vision backends. Each has different capabilities, costs, and tradeoffs.

## Comparison

| | Gemini | OpenAI | Ollama |
|---|---|---|---|
| **Model** | Gemini 2.0 Flash | GPT-4o | qwen3-vl (default) |
| **Video analysis** | Direct upload | Frame-by-frame | Frame-by-frame |
| **Audio transcription** | Yes (native) | Yes (Whisper) | No |
| **API key required** | GEMINI_API_KEY | OPENAI_API_KEY | None |
| **Cost per video** | ~$0.15 | ~$0.20 | Free |
| **Speed** | Fast | Moderate | Depends on hardware |
| **Privacy** | Cloud | Cloud | Fully local |

## When to use which

**Gemini** -- Best overall choice. Supports direct video upload for short videos (under 2 minutes / 20MB), native audio transcription, and fast processing. Cheapest cloud option.

**OpenAI** -- Good if you already have an OpenAI API key and prefer to stay in that ecosystem. Uses GPT-4o for vision and Whisper for audio. Slightly more expensive than Gemini. No direct video upload -- always uses frame-by-frame analysis.

**Ollama** -- Best for privacy and offline use. Runs entirely on your machine with no data sent to external APIs. No audio transcription. Requires a machine with enough RAM for the vision model (8GB+ recommended). Quality depends on the model and hardware.

## Analysis strategy

The backend determines the analysis strategy:

| Strategy | When used | How it works |
|---|---|---|
| **Direct upload** | Gemini, video under 2min/20MB | Full video sent to the API in one request |
| **Frame-by-frame** | OpenAI, Ollama, or large videos | Key frames extracted and analyzed individually |

Frame-by-frame is always used when:

- The backend does not support direct video upload (OpenAI, Ollama)
- The video exceeds 2 minutes or 20MB (even with Gemini)
- The input is an image/screenshot

## Switching backends

```bash
# Via environment variable
export EYEROLL_BACKEND=ollama

# Via CLI flag
eyeroll watch video.mp4 --backend openai

# Via eyeroll init
eyeroll init
```

The `--backend` flag overrides the environment variable for a single run.
