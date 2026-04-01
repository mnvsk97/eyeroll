---
name: watch-video
description: >
  Analyze videos, screen recordings, and screenshots to generate
  structured, actionable notes for coding agents. Supports Loom,
  YouTube, and local files. Extracts visual context, on-screen text,
  and audio narration.
version: 0.1.0
metadata:
  clawdbot:
    requires:
      env:
        - GEMINI_API_KEY
      bins:
        - python3
        - ffmpeg
    primaryEnv: GEMINI_API_KEY
    homepage: https://github.com/mnvsk97/eyeroll
---

# Watch Video

Watch a video, screen recording, or screenshot and produce structured, actionable notes that a coding agent can act on.

## What This Skill Does

Given a video (Loom, YouTube, local file) or screenshot, this skill:

1. Downloads the media (if URL) or reads the local file
2. Extracts key frames and audio from videos
3. Uses Gemini Flash to analyze visual content (UI state, text, user actions)
4. Transcribes audio narration (if present)
5. Synthesizes everything into structured notes with:
   - What's shown and what's happening
   - Exact text visible on screen (errors, URLs, labels, code)
   - What was said (audio transcript)
   - Key observations and actionable takeaways
   - Confidence level and clarifying questions

The notes are designed to give a coding agent enough context to take any action — fix a bug, build a feature, create a skill, write documentation, or implement what was demonstrated.

## Setup

Requires Python 3.11+, ffmpeg, and a Gemini API key.

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install .
eyeroll init
```

Or set the API key directly: `export GEMINI_API_KEY=your-key`

For URL downloads (Loom, YouTube), install yt-dlp: `brew install yt-dlp`

## Commands

### Analyze a video or screenshot

```bash
eyeroll watch <source> [--context "..."] [--max-frames 20] [--output report.md] [--verbose]
```

- `source`: URL (Loom, YouTube, any yt-dlp supported site) or local file path (.mp4, .webm, .mov, .png, .jpg, .gif)
- `--context`: Text context from the person who shared the video — Slack message, issue description, PR reference. Significantly improves analysis quality.
- `--max-frames`: Maximum frames to extract from video (default: 20)
- `--output`: Write notes to file instead of stdout
- `--verbose`: Show progress details

## When To Use This Skill

- User shares a video or screenshot and wants the agent to understand it
- User pastes a Loom or YouTube link
- User says "watch this", "look at this recording", "look at this video"
- User asks to fix a bug based on a video or screenshot
- User asks to build something based on a demo video
- User asks to create a skill/plugin/subagent from a tutorial video
- User shares a screen recording with context about what to do with it
- User asks to generate notes, a report, or documentation from a video

## Example Interactions

User: "Watch this video and tell me what's wrong: https://loom.com/share/abc123"
Action: Run `eyeroll watch https://loom.com/share/abc123`

User: "Here's a recording of the bug. Checkout is broken after billing migration."
Action: Run `eyeroll watch <video_path> --context "checkout broken after billing migration merge"`

User: "Watch this demo and build something similar"
Action: Run `eyeroll watch <url>`, review the notes, then implement the demonstrated feature.

User: "Watch this tutorial and create a skill from it"
Action: Run `eyeroll watch <url> --context "create a skill based on this tutorial"`, then use the notes to generate a SKILL.md and implementation.

User: "Look at this screenshot, what's going on?"
Action: Run `eyeroll watch screenshot.png`

User: "Watch this and raise a PR"
Action: Run `eyeroll watch <url>`, review the notes, search codebase for relevant files, implement the change, and create a PR.

## Rules

- Always check that GEMINI_API_KEY is set before running analysis.
- If ffmpeg is not on PATH, the bundled imageio-ffmpeg fallback is used.
- For videos under 20MB and 2 minutes, the full video is sent to Gemini directly (more accurate). Longer videos use frame-by-frame analysis.
- When context is available (--context), always include it — it dramatically improves quality, especially for silent recordings.
- Do NOT hallucinate text, error messages, or code. Only report what is actually visible/audible.
- If the video is ambiguous or unclear, output clarifying questions rather than guessing.
- The notes are a starting point — when the user asks to take action (fix, build, create), use the notes plus codebase context to do so.
- Warn the user if yt-dlp is not installed when they provide a URL.

## Supported Input Types

| Input | Supported | Notes |
|-------|-----------|-------|
| Local video (.mp4, .webm, .mov, .avi, .mkv) | Yes | Direct analysis |
| Local image (.png, .jpg, .gif, .webp, .bmp) | Yes | Single-frame analysis |
| YouTube URL | Yes | Requires yt-dlp |
| Loom URL | Yes | Requires yt-dlp |
| Any yt-dlp supported URL | Yes | 1000+ sites supported |
| Direct video URL (.mp4 link) | Yes | Requires yt-dlp |

## Cost

Gemini 2.0 Flash pricing (approximate):
- Short video (<2min, direct upload): ~$0.01-0.05 per analysis
- Long video (frame-by-frame, 20 frames): ~$0.02-0.10 per analysis
- Audio transcription: ~$0.01 per minute
- Synthesis: ~$0.01 per report

Total: typically under $0.15 per video analysis.
