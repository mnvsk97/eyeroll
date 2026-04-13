# Cerebras Backend

[Cerebras](https://cerebras.ai) provides fast inference on custom hardware. Uses the same multi-frame batch strategy as OpenAI.

## Setup

1. Get an API key from [cerebras.ai](https://cerebras.ai)
2. Run `eyeroll init` and select Cerebras, or set it directly:

```bash
export CEREBRAS_API_KEY=your-key-here
export EYEROLL_BACKEND=cerebras
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

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --backend cerebras
```

## How it works

Cerebras uses the OpenAI-compatible API format. eyeroll sends all extracted frames as base64-encoded images in a single API call, with timestamps per frame. No audio transcription is available.

## Cost

Competitive pricing with fast inference. Check [cerebras.ai](https://cerebras.ai) for current rates.

## Install

```bash
pip install eyeroll[openai]
```

Uses the `openai` SDK with a custom base URL.
