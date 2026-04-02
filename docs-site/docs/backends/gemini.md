# Gemini Backend

Google Gemini Flash API. The default and recommended backend.

## Setup

### Option 1: API key (simplest)

1. Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Run `eyeroll init` and paste the key, or set it directly:

```bash
export GEMINI_API_KEY=your-key-here
```

### Option 2: Service account (for teams / CI)

For automated or team use, eyeroll supports Google service account credentials:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1   # optional, defaults to us-central1
```

eyeroll also checks these paths automatically:

- `~/.eyeroll/credentials.json`
- `./credentials.json`

Service account auth uses Vertex AI under the hood.

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | Yes (under 2 min / 20MB) |
| Frame-by-frame analysis | Yes (fallback for large videos) |
| Audio transcription | Yes (native) |
| Text generation | Yes |

## Model

Default model: `gemini-2.0-flash`

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --model gemini-2.0-flash
```

## Direct video upload

For short videos (under 2 minutes, under 20MB), Gemini receives the full video in a single API call. This produces better results than frame-by-frame because the model sees motion, transitions, and timing.

For longer or larger videos, eyeroll falls back to frame-by-frame analysis automatically.

## Cost

Gemini Flash is one of the cheapest vision APIs available. A typical 1-minute video costs approximately $0.15, depending on frame count and video length.

!!! tip "Free tier"
    Gemini API has a generous free tier. For occasional use, you may not need to pay at all.

## Install

```bash
pip install eyeroll[gemini]
```

This installs the `google-genai` SDK.
