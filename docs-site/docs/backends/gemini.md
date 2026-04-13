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
- `~/credentials.json`
- `./credentials.json`

You can also configure this via `eyeroll init` -- it will ask whether you want to use an API key or a credentials.json file.

Service account auth uses Vertex AI under the hood.

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | Yes -- File API up to 2GB (API key) or 20MB inline (service account) |
| Frame-by-frame analysis | Yes (fallback for videos exceeding limits) |
| Audio transcription | Yes (native) |
| Text generation | Yes |
| Preflight health check | Yes (verifies model access) |

## Model

Default model: `gemini-2.0-flash`

Override with the `--model` flag:

```bash
eyeroll watch video.mp4 --model gemini-2.0-flash
```

## Direct video upload

With an **API key**, eyeroll uses the Gemini File API to upload videos up to 2GB. The model receives the full video in a single request, producing better results than frame-by-frame because it sees motion, transitions, and timing.

With a **service account** (Vertex AI), videos are sent as inline bytes with a 20MB limit. Videos exceeding this fall back to frame-by-frame automatically.

For videos exceeding either limit, eyeroll falls back to frame-by-frame analysis.

## Cost

Gemini Flash is one of the cheapest vision APIs available. A typical 1-minute video costs approximately $0.15, depending on frame count and video length.

!!! tip "Free tier"
    Gemini API has a generous free tier. For occasional use, you may not need to pay at all.

## Install

```bash
pip install eyeroll[gemini]
```

This installs the `google-genai` SDK.
