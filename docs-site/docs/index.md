# eyeroll

**AI eyes that roll through video footage -- watch, understand, act.**

eyeroll is a Claude Code plugin that analyzes screen recordings, Loom videos, YouTube links, and screenshots, then produces structured reports that coding agents can act on -- fix bugs, build features, create skills.

## What it does

1. You share a video or screenshot (URL or local file)
2. eyeroll extracts frames, analyzes them with a vision model, transcribes audio
3. It classifies the content (bug report, tutorial, feature demo, etc.) and produces a structured report
4. Your coding agent uses the report to fix bugs, create skills, build features, or take notes

## Quick install

```bash
# Add the plugin to Claude Code
npx skills add mnvsk97/eyeroll

# Install the CLI with your preferred backend
pip install eyeroll[gemini]
```

Then run `/eyeroll:init` in Claude Code to configure your backend and generate codebase context.

## Next steps

- [Install guide](getting-started/install.md) -- all installation options
- [Setup](getting-started/setup.md) -- configure your backend and API key
- [Quick start](getting-started/quickstart.md) -- analyze your first video in 3 steps
