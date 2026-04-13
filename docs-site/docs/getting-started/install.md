# Install

## Claude Code plugin

Add the eyeroll plugin to Claude Code:

```bash
/plugin marketplace add mnvsk97/eyeroll
/plugin install eyeroll@mnvsk97-eyeroll
```

This registers the `/eyeroll:watch`, `/eyeroll:fix`, `/eyeroll:init`, and `/eyeroll:history` slash commands.

## CLI installation

Install the Python CLI with the backend you want:

=== "Gemini (recommended)"

    ```bash
    pip install eyeroll[gemini]
    ```

=== "OpenAI"

    ```bash
    pip install eyeroll[openai]
    ```

=== "Ollama (local, no API key)"

    ```bash
    pip install eyeroll
    ```

=== "Everything"

    ```bash
    pip install eyeroll[all]
    ```

!!! tip "URL downloads"
    `yt-dlp` is included as a core dependency. URL downloads (YouTube, Loom, etc.) work out of the box with any install method.

## Prerequisites

| Requirement | Why | Install |
|---|---|---|
| Python 3.11+ | Runtime | [python.org](https://www.python.org/downloads/) |
| ffmpeg | Frame extraction, audio extraction | `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux) |
| yt-dlp | Downloading from URLs | Included as a dependency |

!!! note "ffmpeg fallback"
    If ffmpeg is not on your PATH, eyeroll falls back to the `imageio-ffmpeg` bundled binary (included as a dependency). System ffmpeg is preferred because it includes ffprobe for more accurate duration detection and audio track detection.

## Verify installation

```bash
eyeroll --help
```

You should see the `init`, `watch`, and `history` commands listed.
