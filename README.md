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
pip install eyeroll    # or: pip install git+https://github.com/mnvsk97/eyeroll.git
eyeroll init           # set up Gemini API key
brew install yt-dlp    # for URL downloads (Loom, YouTube)
```

Or just set the key: `export GEMINI_API_KEY=your-key` ([get one free](https://aistudio.google.com/apikey))

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
eyeroll watch https://loom.com/share/abc123
eyeroll watch ./bug.mp4 --context "checkout broken after PR #432"
eyeroll watch screenshot.png --verbose
```

## How it works

```
Video (Loom / YouTube / local file / screenshot)
    ↓
eyeroll extracts: frames, audio, on-screen text
    ↓
Gemini Flash analyzes: what's shown, what's said, what happened
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
- Gemini API key ([free](https://aistudio.google.com/apikey))

## Cost

Typically under $0.15 per video analysis using Gemini 2.0 Flash.

## License

MIT
