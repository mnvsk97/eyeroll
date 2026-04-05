# Quick Start

Three steps to analyze your first video.

## 1. Install

```bash
/plugin marketplace add mnvsk97/eyeroll
/plugin install eyeroll@mnvsk97-eyeroll
pip install eyeroll[gemini]
```

## 2. Initialize

```
/eyeroll:init
```

This configures your API key and generates codebase context. Takes about 30 seconds.

## 3. Watch a video

```
/eyeroll:watch https://loom.com/share/abc123
```

Or with a local file:

```
/eyeroll:watch ./bug-recording.mp4
```

## Example flow

```
You: /eyeroll:watch https://loom.com/share/abc123 --context "checkout page broken after PR #432"

eyeroll: Acquiring: https://loom.com/share/abc123
         Media type: video
         Duration: 00:45
         Strategy: frame-by-frame
         Extracted 12 key frames
         Analyzing frame 0 @ 00:00...
         Analyzing frame 1 @ 00:04...
         ...
         Synthesizing report...

Agent:   Here's what the video shows:

         **What's happening**: The user navigates to /checkout, fills in payment
         details, clicks "Pay", and gets a 500 error. The error toast reads
         "Internal Server Error".

         **The bug**: POST /api/checkout returns 500. The console shows
         "TypeError: Cannot read properties of undefined (reading 'stripe_id')".

         **Key evidence**:
         - Error: "TypeError: Cannot read properties of undefined (reading 'stripe_id')"
         - Route: /api/checkout (POST)
         - The error appears after clicking the "Pay" button

         **Suggested fix**: Search for `stripe_id` in the checkout handler.
         The user object may not have a Stripe customer ID set.

         Want me to fix this?
```

## Adding context

Context text helps eyeroll understand what you want. Most screen recordings are silent, so the context is often more informative than the video itself.

```
/eyeroll:watch ./demo.mp4 --context "create a skill from this tutorial"
/eyeroll:watch ./bug.mp4 --context "broken after deploying the auth changes"
```

## What's next

- [/eyeroll:fix](../commands/fix.md) -- go from video to PR in one command
- [Backends](../backends/overview.md) -- compare Gemini, OpenAI, and Ollama
- [How it works](../how-it-works.md) -- understand the pipeline
