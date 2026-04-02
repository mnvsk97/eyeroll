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
| Frame-by-frame analysis | Yes |
| Audio transcription | Yes (Whisper) |
| Text generation | Yes |

## Model

Default model: `gpt-4o`

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --backend openai --model gpt-4o
```

!!! note "Model inference"
    If you pass a model name starting with `gpt` or `o1` or `o3` without specifying `--backend`, eyeroll automatically selects the OpenAI backend.

## How it works

OpenAI does not support direct video upload. eyeroll always uses the frame-by-frame strategy:

1. Extract key frames from the video
2. Send each frame as a base64-encoded image to GPT-4o
3. Transcribe audio using Whisper (`whisper-1` model)
4. Synthesize the report from frame analyses and transcript

## Audio transcription

Audio is transcribed via the Whisper API (`whisper-1` model). This runs automatically when the video has an audio track. Silent recordings are detected and skipped.

## Cost

A typical 1-minute video with 10-15 frames costs approximately $0.20, depending on image resolution and audio length.

## Install

```bash
pip install eyeroll[openai]
```

This installs the `openai` SDK.
