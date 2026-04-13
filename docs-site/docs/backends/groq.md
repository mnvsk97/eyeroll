# Groq Backend

[Groq](https://groq.com) provides extremely fast inference. Uses the same multi-frame batch strategy as OpenAI.

## Setup

1. Get an API key at [console.groq.com](https://console.groq.com)
2. Run `eyeroll init` and select Groq, or set it directly:

```bash
export GROQ_API_KEY=your-key-here
export EYEROLL_BACKEND=groq
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
eyeroll watch video.mp4 --backend groq -m llama-3.2-90b-vision-preview
```

## How it works

Groq uses the OpenAI-compatible API format. eyeroll sends all extracted frames as base64-encoded images in a single API call, with timestamps per frame. No audio transcription is available.

## Cost

Groq offers competitive pricing with very low latency. Check [groq.com](https://groq.com) for current rates.

## Install

```bash
pip install eyeroll[openai]
```

Uses the `openai` SDK with a custom base URL.
