---
name: watch-video
description: >
  Analyze videos, screen recordings, and screenshots to generate
  structured, actionable notes for coding agents. Supports Loom,
  YouTube, and local files. First explores the codebase for context,
  then processes the video with that understanding. Use when someone
  shares a video and you need to understand what it shows.
compatibility: "Requires Python 3.11+, ffmpeg, GEMINI_API_KEY"
---

# Watch Video

Watch a video, screen recording, or screenshot and produce structured, actionable notes grounded in codebase context.

## What This Skill Does

1. **Explores the codebase first** — reads key files to understand the project
2. Downloads and analyzes the video using Gemini Flash or Ollama
3. Produces a report with bug descriptions, fix directions, and search patterns grounded in actual project files

## Setup

Requires Python 3.11+ and ffmpeg.

```bash
pip install eyeroll
eyeroll init          # or: export GEMINI_API_KEY=your-key
brew install yt-dlp   # for Loom/YouTube URLs
```

For local-only analysis: `ollama serve` (no API key needed)

## Workflow

### Step 1: Get codebase context

Check if `.eyeroll/context.md` exists:
- **If yes**: Use it. Pass it via `--codebase-context .eyeroll/context.md`
- **If no**: Run `/eyeroll:init` first to generate it, OR quickly read `CLAUDE.md`/`README.md` and pass a short inline summary.

### Step 2: Run eyeroll

```bash
eyeroll watch <source> \
  --context "user's description of what to look for" \
  --codebase-context .eyeroll/context.md \
  --verbose
```

- `--context` / `-c`: What the user said about the video
- `--codebase-context` / `-cc`: Path to `.eyeroll/context.md` or inline text
- `--backend` / `-b`: `gemini` (default) or `ollama`
- `--output` / `-o`: Write report to file

### Step 3: Act on the report

The report contains:
- **Bug Description**: What's broken, expected vs actual behavior
- **Fix Directions**: Categorized as "Visible in recording", "Informed by codebase context", or "Hypothesis"
- **Suggested search patterns**: grep commands to find relevant code
- **How to fix**: Concrete steps referencing actual project files

Use these to search the codebase, find the relevant code, and take action.

## When To Use This Skill

- User shares a video or screenshot and wants to understand it
- User pastes a Loom or YouTube link
- User says "watch this", "look at this recording", "look at this video"
- User asks to fix a bug based on a video
- User asks to build something based on a demo video
- User shares a screen recording with context

## Example Interactions

User: "Watch this video and tell me what's wrong: https://loom.com/share/abc123"
```
1. Check for .eyeroll/context.md (if missing, suggest /eyeroll:init)
2. eyeroll watch https://loom.com/share/abc123 -cc .eyeroll/context.md
3. Read report, grep for error strings mentioned, present findings
```

User: "Checkout is broken after billing migration, here's a recording"
```
1. eyeroll watch video.mp4 \
     -c "checkout broken after billing migration" \
     -cc .eyeroll/context.md
2. Cross-reference report findings with codebase
3. Present diagnosis
```

## Rules

- Check for `.eyeroll/context.md` first. If missing, suggest running `/eyeroll:init`.
- Check that `GEMINI_API_KEY` is set (or use `--backend ollama` for local).
- Always include `--context` when the user provides description of the video.
- A report without codebase context produces hypothetical file paths — always pass context.
- If the report's confidence is low or the video is ambiguous, ask clarifying questions before acting.
- Warn the user if yt-dlp is not installed when they provide a URL.
