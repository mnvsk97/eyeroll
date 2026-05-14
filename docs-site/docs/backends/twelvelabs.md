# TwelveLabs Backend

TwelveLabs direct video understanding through Pegasus 1.5.

Use this backend when you want a video-native model to watch the full recording and produce the final eyeroll report directly. It is intentionally lean: no frame extraction, no separate audio pass, and no second synthesis call.

## Setup

1. Create a TwelveLabs API key in the TwelveLabs playground.
2. Run `eyeroll init` and choose `twelvelabs`, or set the key directly:

```bash
export TWELVE_LABS_API_KEY=your-key-here
```

Then run:

```bash
eyeroll watch ./bug.mp4 --backend twelvelabs
```

## Capabilities

| Feature | Supported |
|---|---|
| Direct video upload | Yes, local files up to 200MB |
| Frame-by-frame fallback | No |
| Audio understanding | Included in video analysis |
| Separate audio transcription | No |
| Text-only synthesis | No |

## How It Works

The backend uploads the video as a TwelveLabs asset, waits until the asset is ready, then asks Pegasus 1.5 to generate the structured eyeroll report. Because the output is already the final report, eyeroll does not run a second synthesis step.

If the video exceeds the supported direct-upload limits, eyeroll fails clearly instead of silently falling back to frame extraction. Use Gemini or OpenAI if you need automatic frame fallback for larger files.

## Model

Default model: `pegasus1.5`

Override with:

```bash
eyeroll watch ./bug.mp4 --backend twelvelabs --model pegasus1.5
```

## Cost

TwelveLabs usage is provider-billed. eyeroll prints `Cost: not estimated` for this backend because it does not currently estimate TwelveLabs video-processing charges.

## Install

```bash
pip install eyeroll[twelvelabs]
```

This installs the `twelvelabs` SDK.
