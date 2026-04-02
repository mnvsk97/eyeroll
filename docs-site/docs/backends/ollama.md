# Ollama Backend

Local vision models via Ollama. Fully private, no API key needed.

## Setup

1. Install Ollama: [ollama.com](https://ollama.com)
2. Start the server:

```bash
ollama serve
```

3. Configure eyeroll:

```bash
export EYEROLL_BACKEND=ollama
```

Or run `eyeroll init` and select Ollama.

!!! tip "Auto-install"
    On macOS and Linux, if Ollama is not installed, eyeroll will attempt to install it automatically and start the server. This happens on first use.

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | No |
| Frame-by-frame analysis | Yes |
| Audio transcription | No |
| Text generation | Yes |

## Models

Default model: `qwen3-vl`

Available vision models for Ollama:

| Model | Size | RAM needed | Quality |
|---|---|---|---|
| `qwen3-vl` | ~5GB | 8GB+ | Good |
| `qwen3-vl:2b` | ~1.5GB | 4GB+ | Acceptable |
| `qwen3-vl:8b` | ~5GB | 8GB+ | Good |

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --backend ollama --model qwen3-vl:2b
```

### Auto-pull

If the specified model is not installed, eyeroll pulls it automatically on first use. Progress is shown in stderr.

## How it works

Ollama only supports image analysis, not direct video or audio. eyeroll always uses the frame-by-frame strategy:

1. Extract key frames from the video
2. Send each frame as a base64-encoded image to the Ollama API
3. Audio transcription is skipped entirely
4. Synthesize the report from frame analyses only

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `EYEROLL_BACKEND` | `gemini` | Set to `ollama` to use this backend |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server address |

## Limitations

- No audio transcription -- narration in videos is lost
- Frame-by-frame only -- no motion or timing context
- Quality depends on model size and hardware
- Slower than cloud backends on most hardware

!!! warning "Silent recordings"
    Most developer screen recordings are silent, so the lack of audio transcription is often not a problem. But if the video has spoken narration, important context will be missed with Ollama.

## Cost

Free. All processing happens locally.

## Install

```bash
pip install eyeroll
```

No extra SDK needed -- Ollama communication uses the standard library (`urllib`).
