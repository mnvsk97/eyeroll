# OpenRouter Backend

Access hundreds of models via [OpenRouter](https://openrouter.ai). Uses the same multi-frame batch strategy as OpenAI.

## Setup

1. Get an API key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Run `eyeroll init` and select OpenRouter, or set it directly:

```bash
export OPENROUTER_API_KEY=your-key-here
export EYEROLL_BACKEND=openrouter
```

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | No |
| Multi-frame batch | Yes (all frames in one API call) |
| Audio transcription | No |
| Text generation | Yes |
| Preflight health check | Yes |

## Model

Default model varies. Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --backend openrouter -m anthropic/claude-3.5-sonnet
eyeroll watch video.mp4 --backend openrouter -m google/gemini-flash-1.5
```

OpenRouter gives you access to models from many providers (Anthropic, Google, Meta, Mistral, etc.) through a single API key.

## How it works

OpenRouter uses the OpenAI-compatible API format. eyeroll sends all extracted frames as base64-encoded images in a single API call, with timestamps per frame. No audio transcription is available.

## Cost

Varies by model. OpenRouter passes through the upstream provider's pricing. Check [openrouter.ai/models](https://openrouter.ai/models) for current rates.

## Install

```bash
pip install eyeroll[openai]
```

Uses the `openai` SDK with a custom base URL.
