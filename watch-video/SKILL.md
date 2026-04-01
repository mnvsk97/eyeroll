---
name: watch-video
description: >
  Analyze bug videos, screen recordings, and screenshots to generate
  structured bug reports. Supports Loom, YouTube, and local files.
  Extracts visual context, error messages, and audio narration to
  produce actionable developer notes.
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
    homepage: https://github.com/mnvsk97/reelfix
---

# Watch Video

Analyze a bug video, screen recording, or screenshot and produce a structured, actionable bug report.

## What This Skill Does

Given a video (Loom, YouTube, local file) or screenshot showing a bug, this skill:

1. Downloads the media (if URL) or reads the local file
2. Extracts key frames and audio from videos
3. Uses Gemini Flash to analyze visual content (UI state, error messages, user actions)
4. Transcribes audio narration (if present)
5. Synthesizes everything into a structured bug report with:
   - Steps to reproduce
   - Exact error messages (via OCR from frames)
   - Expected vs actual behavior
   - Confidence level
   - Clarifying questions (if the bug is ambiguous)

The bug report is designed to give a coding agent enough context to find the relevant code and implement a fix.

## Setup

Requires Python 3.11+, ffmpeg, and a Gemini API key.

```bash
git clone https://github.com/mnvsk97/reelfix.git
cd reelfix
pip install .
reelfix init
```

Or set the API key directly: `export GEMINI_API_KEY=your-key`

For URL downloads (Loom, YouTube), install yt-dlp: `brew install yt-dlp`

## Commands

### Analyze a video or screenshot

```bash
reelfix watch <source> [--context "..."] [--max-frames 20] [--output report.md] [--verbose]
```

- `source`: URL (Loom, YouTube, any yt-dlp supported site) or local file path (.mp4, .webm, .mov, .png, .jpg, .gif)
- `--context`: Text context from the reporter — Slack message, issue description, PR reference. This significantly improves analysis quality.
- `--max-frames`: Maximum frames to extract from video (default: 20)
- `--output`: Write report to file instead of stdout
- `--verbose`: Show progress details

## When To Use This Skill

- User shares a video or screenshot of a bug and wants to understand or fix it
- User pastes a Loom or YouTube link showing broken behavior
- User says "watch this", "look at this recording", "here's the bug"
- User asks to fix a bug based on a video or screenshot
- User asks to generate a bug report from a recording
- User shares a screen recording with context like "this is broken"

## Example Interactions

User: "Watch this video and tell me what's wrong: https://loom.com/share/abc123"
Action: Run `reelfix watch https://loom.com/share/abc123`

User: "Here's a recording of the bug. The checkout page is broken after we merged the billing migration."
Action: Run `reelfix watch <video_path> --context "checkout page is broken after billing migration merge"`

User: "Can you look at this screenshot? Getting this error for admin users."
Action: Run `reelfix watch screenshot.png --context "error appearing for admin users"`

User: "Watch this and fix it" (with a video URL)
Action: First run `reelfix watch <url>`, review the bug report, then use the report to search the codebase and implement a fix.

User: "Watch this video and raise a PR"
Action: Run `reelfix watch <url>`, review the bug report, search codebase for relevant files, implement the fix, and create a PR linking back to the video.

## Rules

- Always check that GEMINI_API_KEY is set before running analysis.
- If ffmpeg is not on PATH, the bundled imageio-ffmpeg fallback is used.
- For videos under 20MB and 2 minutes, the full video is sent to Gemini directly (more accurate). Longer videos use frame-by-frame analysis.
- When reporter context is available (--context), always include it — it dramatically improves bug report quality, especially for silent recordings.
- Do NOT hallucinate error messages or code paths. Only report what is actually visible/audible in the recording.
- If the video is ambiguous or unclear, output clarifying questions rather than guessing.
- When the user asks to "fix it" or "raise a PR" after watching, use the bug report to search the codebase and implement the fix — the bug report alone is not the final output.
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
