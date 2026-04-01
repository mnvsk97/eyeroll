# eyeroll

AI eyes that roll through video footage — watch, understand, act.

eyeroll analyzes screen recordings, Loom videos, YouTube links, and screenshots, then produces structured notes that AI coding agents can act on — fix bugs, build features, create skills, generate subagents, or anything else.

## How it works

```
Video (Loom / YouTube / local file / screenshot)
    ↓
eyeroll extracts: frames, audio, on-screen text
    ↓
Gemini Flash analyzes: what's shown, what's said, what's on screen
    ↓
Structured notes: what happened, key details, actionable context
    ↓
Feed to Claude Code / Codex → understand → act
```

## Use cases

- **Bug video → fix → PR**: QA sends a recording, eyeroll understands the bug, agent fixes it
- **Demo video → build feature**: Watch a product demo, build something similar
- **Tutorial → skill/plugin**: Watch a walkthrough, generate a skill from it
- **Architecture video → implementation**: Watch a design review, implement it
- **Any video → structured notes**: Turn any screen recording into actionable developer context

## Quick start

```bash
pip install .
eyeroll init          # set up Gemini API key
eyeroll watch https://loom.com/share/abc123
```

With context (significantly improves quality):

```bash
eyeroll watch ./recording.mp4 --context "checkout broken after billing migration PR"
```

## Supported inputs

| Input | Notes |
|-------|-------|
| Loom URLs | Requires yt-dlp |
| YouTube URLs | Requires yt-dlp |
| Local video files (.mp4, .webm, .mov) | Direct analysis |
| Screenshots (.png, .jpg, .gif) | Single-frame analysis |
| Any yt-dlp supported URL | 1000+ sites |

## As a Claude Code skill

eyeroll ships as a Claude Code skill. Use `/watch` in your conversations:

```
User: watch this and fix it: https://loom.com/share/abc123
User: watch this tutorial and create a skill from it: ./demo.mp4
User: look at this screenshot, what's wrong? [screenshot.png]
```

The skill produces structured notes, then Claude Code uses its codebase context to take action.

## Requirements

- Python 3.11+
- ffmpeg (`brew install ffmpeg`)
- yt-dlp (`brew install yt-dlp`) — for URL downloads
- Gemini API key ([free](https://aistudio.google.com/apikey))

## Cost

Typically under $0.15 per video analysis using Gemini 2.0 Flash.

## License

MIT
