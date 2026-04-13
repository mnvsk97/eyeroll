# OpenAI Backend

OpenAI GPT-4o for vision analysis and Whisper for audio transcription.

## Setup

1. Get an API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Run `eyeroll init` and select OpenAI, or set it directly:

```bash
export OPENAI_API_KEY=your-key-here
export EYEROLL_BACKEND=openai
```

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | No |
| Multi-frame batch | Yes (all frames in one API call) |
| Audio transcription | Yes (Whisper) |
| Text generation | Yes |
| Preflight health check | Yes (verifies API key) |

## Model

Default model: `gpt-4o`

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --backend openai --model gpt-4o
```

!!! note "Model inference"
    If you pass a model name starting with `gpt` or `o1` or `o3` without specifying `--backend`, eyeroll automatically selects the OpenAI backend.

## How it works

OpenAI does not support direct video upload. eyeroll uses the **multi-frame batch** strategy:

1. Extract key frames from the video
2. Send all frames as base64-encoded images in a single API call to GPT-4o, with timestamps per frame
3. Transcribe audio using Whisper (`whisper-1` model)
4. Synthesize the report from the batch analysis and transcript

This is more efficient than frame-by-frame (one API call instead of N) and gives the model temporal context across all frames.

## OpenAI-compatible providers

The OpenAI backend also powers OpenRouter, Groq, Grok, Cerebras, and custom endpoints. These use the same multi-frame batch strategy but without Whisper audio transcription.

```bash
eyeroll watch video.mp4 --backend openrouter
eyeroll watch video.mp4 --backend groq
eyeroll watch video.mp4 --backend openai-compat --base-url https://my-server/v1
```

## Audio transcription

Audio is transcribed via the Whisper API (`whisper-1` model). This runs automatically when the video has an audio track. Silent recordings are detected and skipped.

## Cost

A typical 1-minute video with 10-15 frames costs approximately $0.20, depending on image resolution and audio length.

## Install

```bash
pip install eyeroll[openai]
```

This installs the `openai` SDK.
