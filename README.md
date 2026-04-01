# reelfix

Watch a bug video. Understand it. Fix it.

reelfix analyzes screen recordings, Loom videos, YouTube links, and screenshots to produce structured bug reports that AI coding agents can use to find and fix the issue.

## How it works

```
Bug video (Loom / YouTube / local file / screenshot)
    ↓
reelfix extracts: frames, audio, on-screen text
    ↓
Gemini Flash analyzes: what happened, what went wrong, exact errors
    ↓
Structured bug report: steps to reproduce, error signals, diagnosis
    ↓
Feed to Claude Code / Codex → codebase search → fix → PR
```

## Quick start

```bash
pip install .
reelfix init          # set up Gemini API key
reelfix watch https://loom.com/share/abc123
```

With reporter context (significantly improves quality):

```bash
reelfix watch ./bug.mp4 --context "checkout broken after billing migration PR"
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

reelfix ships as a Claude Code skill. Install it and use `/watch` in your conversations:

```
/watch https://loom.com/share/abc123 --context "payments page is broken"
```

The skill produces a bug report, then Claude Code uses its codebase context to find relevant files, diagnose the issue, and optionally raise a PR.

## Requirements

- Python 3.11+
- ffmpeg (`brew install ffmpeg`)
- yt-dlp (`brew install yt-dlp`) — for URL downloads
- Gemini API key ([free](https://aistudio.google.com/apikey))

## Cost

Typically under $0.15 per video analysis using Gemini 2.0 Flash.

## License

MIT
