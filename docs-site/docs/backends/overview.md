# Backends

eyeroll supports multiple vision backends. Each has different capabilities, costs, and tradeoffs.

## Comparison

| | Gemini | OpenAI | Ollama | OpenRouter / Groq / Grok / Cerebras |
|---|---|---|---|---|
| **Model** | Gemini 2.0 Flash | GPT-4o | qwen3-vl (default) | Varies by provider |
| **Strategy** | Direct upload | Multi-frame batch | Frame-by-frame | Multi-frame batch |
| **Audio** | Yes (native) | Yes (Whisper) | No | No |
| **API key** | GEMINI_API_KEY | OPENAI_API_KEY | None | Provider-specific |
| **Cost per video** | ~$0.15 | ~$0.20 | Free | Varies |
| **Privacy** | Cloud | Cloud | Fully local | Cloud |

## When to use which

**Gemini** -- Best overall. Direct video upload via File API (up to 2GB with API key, 20MB with service account). Native audio transcription. Cheapest cloud option.

**OpenAI** -- Good if you already have an OpenAI key. Uses multi-frame batch (all frames in one API call) for efficiency. Whisper for audio. Slightly more expensive than Gemini.

**OpenRouter / Groq / Grok / Cerebras** -- OpenAI-compatible providers. Same multi-frame batch strategy as OpenAI. Useful for model variety (OpenRouter), low latency (Groq), or specific model families.

**Ollama** -- Best for privacy and offline use. Runs entirely on your machine. No audio transcription. Frame-by-frame (one frame per API call). Quality depends on the model and hardware.

**openai-compat** -- Any OpenAI-compatible endpoint. Use `--base-url` to point at your own server.

## Analysis strategy

eyeroll runs a preflight check to detect backend capabilities, then chooses the best strategy:

| Strategy | When used | How it works |
|---|---|---|
| **Direct upload** | Gemini (within size limits) | Full video uploaded via File API in one request |
| **Multi-frame batch** | OpenAI, OpenRouter, Groq, Grok, Cerebras | All frames sent as images in a single API call |
| **Frame-by-frame** | Ollama, or fallback for very large videos | Each frame analyzed in a separate API call |

The strategy is chosen automatically based on what the backend reports it can do. You don't need to configure it.

## Switching backends

```bash
# Via environment variable
export EYEROLL_BACKEND=ollama

# Via CLI flag
eyeroll watch video.mp4 --backend openai
eyeroll watch video.mp4 --backend groq
eyeroll watch video.mp4 --backend openai-compat --base-url https://my-server/v1

# Via eyeroll init
eyeroll init
```

The `--backend` flag overrides the environment variable for a single run.
