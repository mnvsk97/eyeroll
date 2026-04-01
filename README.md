# eyeroll

AI eyes that roll through video footage — watch, understand, act.

eyeroll is a collection of AI coding agent skills that analyze screen recordings, Loom videos, YouTube links, and screenshots, then turn them into code actions.

## Skills

| Skill | What it does |
|-------|-------------|
| **watch-video** | Watch a video and produce structured notes |
| **video-to-pr** | Watch a bug video → diagnose → fix → raise PR |
| **video-to-skill** | Watch a tutorial/demo → generate a Claude Code skill |

## Install

```bash
# Install all skills
npx skills add mnvsk97/eyeroll

# Install a specific skill
npx skills add mnvsk97/eyeroll@video-to-pr
npx skills add mnvsk97/eyeroll@video-to-skill
npx skills add mnvsk97/eyeroll@watch-video
```

## Setup

```bash
pip install eyeroll
brew install yt-dlp    # for URL downloads (Loom, YouTube)
```

### Option A: Gemini (default, API-based)

```bash
eyeroll init           # or: export GEMINI_API_KEY=your-key
```

Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Supports direct video upload, audio transcription. ~$0.15 per analysis.

### Option B: Ollama + Qwen3-VL (local, private, free)

```bash
brew install ollama    # install Ollama
ollama serve           # start the server
```

No API key needed. The model is pulled automatically on first use (~6GB for qwen3-vl:8b). Runs entirely on your machine.

## Usage

### In Claude Code (via skills)

```
User: fix this bug: https://loom.com/share/abc123
      → video-to-pr skill activates, watches video, finds code, fixes, raises PR

User: watch this tutorial and create a skill from it: ./demo.mp4
      → video-to-skill skill activates, watches video, generates SKILL.md

User: look at this recording, what's going on?
      → watch-video skill activates, produces structured notes
```

### Standalone CLI

```bash
# Gemini (default)
eyeroll watch https://loom.com/share/abc123
eyeroll watch ./bug.mp4 --context "checkout broken after PR #432"

# Ollama (local)
eyeroll watch ./bug.mp4 --backend ollama
eyeroll watch screenshot.png -b ollama -m qwen3-vl:2b

# Or set as default
export EYEROLL_BACKEND=ollama
eyeroll watch ./recording.mp4
```

## Backends

| Backend | Video | Audio | API Key | Cost | Best for |
|---------|-------|-------|---------|------|----------|
| **gemini** | Direct upload | Yes | Required | ~$0.15/video | Best quality, short videos |
| **ollama** | Frame-by-frame | No | None | Free | Privacy, offline, no API limits |

### Ollama models

| Model | Size | Notes |
|-------|------|-------|
| `qwen3-vl` (default) | 6.1GB | Best quality, needs 8GB+ RAM |
| `qwen3-vl:2b` | 1.9GB | Lighter, works on 8GB machines |
| `qwen3-vl:32b` | 21GB | Higher quality, needs 32GB+ RAM |

## How it works

```
Video (Loom / YouTube / local file / screenshot)
    ↓
eyeroll extracts: frames, audio, on-screen text
    ↓
Backend analyzes: Gemini Flash (API) or Qwen3-VL (local via Ollama)
    ↓
Structured notes → skill decides what to do next
    ↓
video-to-pr:    search codebase → fix → PR
video-to-skill: extract workflow → generate SKILL.md
watch-video:    return notes to the agent
```

## Supported inputs

| Input | Notes |
|-------|-------|
| Loom URLs | Requires yt-dlp |
| YouTube URLs | Requires yt-dlp |
| Local video files (.mp4, .webm, .mov) | Direct analysis |
| Screenshots (.png, .jpg, .gif) | Single-frame analysis |
| Any yt-dlp supported URL | 1000+ sites |

## Requirements

- Python 3.11+
- ffmpeg (`brew install ffmpeg`)
- yt-dlp (`brew install yt-dlp`) — for URL downloads
- **Gemini backend:** Gemini API key ([free](https://aistudio.google.com/apikey))
- **Ollama backend:** [Ollama](https://ollama.com) installed and running

## License

MIT
