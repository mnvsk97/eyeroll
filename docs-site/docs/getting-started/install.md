# Install

## Claude Code plugin

Add the eyeroll skill to Claude Code:

```bash
npx skills add mnvsk97/eyeroll
```

This registers the `/eyeroll:watch`, `/eyeroll:fix`, `/eyeroll:init`, and `/eyeroll:history` slash commands.

## CLI installation

Install the Python CLI with the backend you want:

=== "Gemini (recommended)"

    ```bash
    pip install eyeroll[gemini,download]
    ```

=== "OpenAI"

    ```bash
    pip install eyeroll[openai,download]
    ```

=== "Ollama (local, no API key)"

    ```bash
    pip install eyeroll[download]
    ```

=== "Everything"

    ```bash
    pip install eyeroll[all]
    ```

The `download` extra installs `yt-dlp` for downloading videos from URLs. If you only analyze local files, you can omit it.

## Prerequisites

| Requirement | Why | Install |
|---|---|---|
| Python 3.11+ | Runtime | [python.org](https://www.python.org/downloads/) |
| ffmpeg | Frame extraction, audio extraction | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| yt-dlp | Downloading from URLs (optional) | Included with `[download]` extra |

!!! note "ffmpeg fallback"
    If ffmpeg is not on your PATH, eyeroll falls back to the `imageio-ffmpeg` bundled binary (included as a dependency). System ffmpeg is preferred because it includes ffprobe for more accurate duration detection and audio track detection.

## Verify installation

```bash
eyeroll --help
```

You should see the `init`, `watch`, and `history` commands listed.
