# Grok Backend

[Grok](https://x.ai) from xAI. Uses the same multi-frame batch strategy as OpenAI.

## Setup

1. Get an API key from [x.ai](https://x.ai)
2. Run `eyeroll init` and select Grok, or set it directly:

```bash
export GROK_API_KEY=your-key-here
export EYEROLL_BACKEND=grok
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
eyeroll watch video.mp4 --backend grok -m grok-2-vision
```

## How it works

Grok uses the OpenAI-compatible API format. eyeroll sends all extracted frames as base64-encoded images in a single API call, with timestamps per frame. No audio transcription is available.

## Cost

Varies. Check [x.ai](https://x.ai) for current pricing.

## Install

```bash
pip install eyeroll[openai]
```

Uses the `openai` SDK with a custom base URL.
