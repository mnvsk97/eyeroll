# OpenAI-Compatible Backend

Point eyeroll at any OpenAI-compatible API endpoint. Use this for self-hosted models, custom proxies, or any provider that implements the OpenAI API format.

## Setup

```bash
export EYEROLL_BACKEND=openai-compat
```

You must provide a base URL via the `--base-url` flag:

```bash
eyeroll watch video.mp4 --backend openai-compat --base-url https://my-server/v1
```

For authentication, set whichever environment variable your endpoint expects (e.g., `OPENAI_API_KEY`).

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
eyeroll watch video.mp4 --backend openai-compat --base-url https://my-server/v1 -m my-model
```

## How it works

Uses the `openai` SDK pointed at your custom base URL. eyeroll sends all extracted frames as base64-encoded images in a single API call, with timestamps per frame. No audio transcription is available.

## Use cases

- **Self-hosted models** -- vLLM, TGI, llama.cpp with OpenAI-compatible server
- **Custom proxies** -- LiteLLM proxy, API gateways
- **Niche providers** -- any service with an OpenAI-compatible vision endpoint

## Install

```bash
pip install eyeroll[openai]
```

Uses the `openai` SDK with a custom base URL.
