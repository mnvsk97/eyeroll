# eyeroll

AI eyes that roll through video footage — watch, understand, act.

eyeroll analyzes screen recordings, Loom videos, YouTube links, and screenshots, then produces structured reports that coding agents can act on — fix bugs, build features, create skills.

## Skills

| Skill | What it does |
|-------|-------------|
| **init** | Set up eyeroll — pick a backend, configure API key, generate codebase context |
| **watch-video** | Watch a video and produce structured notes grounded in codebase context |
| **video-to-pr** | Watch a bug video → diagnose → fix → raise PR |
| **video-to-skill** | Watch a tutorial/demo → generate a Claude Code skill |
| **history** | List and manage past video analyses |

## Install

```bash
# Install skills for Claude Code
npx skills add mnvsk97/eyeroll

# Install CLI
pip install eyeroll              # core (Ollama only)
pip install eyeroll[gemini]      # + Gemini Flash API
pip install eyeroll[openai]      # + OpenAI GPT-4o
pip install eyeroll[all]         # everything

# For URL downloads (Loom, YouTube)
brew install yt-dlp
```

## Setup

```bash
eyeroll init
```

Interactive setup — pick your backend and configure:

```
Which backend do you want to use?

  1. gemini  — Google Gemini Flash API (fast, cheap, best quality)
  2. openai  — OpenAI GPT-4o (great vision, Whisper audio)
  3. ollama  — Local models via Ollama (private, no API key)
```

## Usage

### In Claude Code (via skills)

```
User: fix this bug: https://loom.com/share/abc123
      → video-to-pr skill activates, watches video, finds code, fixes, raises PR

User: watch this tutorial and create a skill from it: ./demo.mp4
      → video-to-skill skill activates, watches video, generates SKILL.md

User: look at this recording, what's going on?
      → watch-video skill activates, produces structured notes
```

### Standalone CLI

```bash
# Basic
eyeroll watch https://loom.com/share/abc123
eyeroll watch ./bug.mp4 --context "checkout broken after PR #432"

# With codebase context (inline or file)
eyeroll watch ./bug.mp4 -cc .eyeroll/context.md
eyeroll watch ./bug.mp4 -cc "FastAPI app, key files: src/api/routes.py"

# Backends
eyeroll watch ./bug.mp4 --backend openai
eyeroll watch ./bug.mp4 -b ollama -m qwen3-vl:2b

# Performance
eyeroll watch ./bug.mp4 --parallel 4          # 3-5x faster frame analysis
eyeroll watch ./bug.mp4 --no-cache            # force fresh analysis

# History
eyeroll history                               # list past analyses
eyeroll history --json                        # JSON output
eyeroll history clear                         # clear cache
```

## Backends

| Backend | Video | Audio | API Key | Cost | Best for |
|---------|-------|-------|---------|------|----------|
| **gemini** | Direct upload | Gemini native | GEMINI_API_KEY | ~$0.15/video | Best quality, short videos |
| **openai** | Frame-by-frame | Whisper | OPENAI_API_KEY | ~$0.20/video | If you already have an OpenAI key |
| **ollama** | Frame-by-frame | No | None | Free | Privacy, offline, no API limits |

## How it works

```
Video (Loom / YouTube / local file / screenshot)
    ↓
1. Acquire: download via yt-dlp or read local file
    ↓
2. Extract: scene detection picks frames where screen changes
           + audio extraction
    ↓
3. Analyze: vision model reads each frame (parallel)
          + audio transcription
    ↓
4. Cache: store intermediates for instant re-use
    ↓
5. Synthesize: combine observations + codebase context
             into structured report with:
             - Bug Description
             - Fix Directions (grounded in codebase context)
             - Suggested search patterns
    ↓
Skills decide what to do next:
  video-to-pr:    search codebase → fix → PR
  video-to-skill: extract workflow → generate SKILL.md
  watch-video:    return report to the agent
```

## Codebase context

eyeroll produces better reports when it knows about your project. The `/eyeroll:init` skill generates `.eyeroll/context.md` — a concise summary of your project that gets passed to the analysis.

```bash
# Claude Code generates context automatically via /eyeroll:init
# Or pass it manually:
eyeroll watch video.mp4 -cc .eyeroll/context.md

# The report's Fix Directions will reference actual files in your project
# instead of hallucinating paths.
```

Without codebase context, all file paths in the report are labeled as hypotheses.

## Supported inputs

| Input | Formats |
|-------|---------|
| **Video** | .mp4, .webm, .mov, .avi, .mkv, .flv, .ts, .m4v, .wmv, .3gp, .mpg, .mpeg, .ogv, .m2ts, .mts |
| **Image** | .png, .jpg, .jpeg, .gif, .webp, .bmp, .tiff, .tif, .heic, .heif, .avif |
| **URL** | YouTube, Loom, Vimeo, Twitter/X, Reddit, and 1000+ sites via yt-dlp |

## Caching

eyeroll caches intermediate analysis results (frame analyses, transcript) in `.eyeroll/cache/`. Same video = instant result, no API cost. Different `--context` or `--codebase-context` re-runs only the cheap synthesis step.

```bash
eyeroll watch video.mp4                    # full analysis (~15s)
eyeroll watch video.mp4 -c "new context"   # instant — reuses cached frames
eyeroll watch video.mp4 --no-cache         # force fresh analysis
eyeroll history                            # see all cached analyses
```

## Requirements

- Python 3.11+
- ffmpeg (`brew install ffmpeg`)
- yt-dlp (`brew install yt-dlp` or `pip install eyeroll[download]`) — for URL downloads

## Development

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install -e '.[dev,all]'

# Unit tests (143 tests, all mocked)
pytest

# Integration tests (real API calls, run before releases)
pytest tests/test_integration.py -v -m integration
```

## License

MIT
