# eyeroll

AI eyes that roll through video footage — watch, understand, act.

eyeroll is a Claude Code plugin that analyzes screen recordings, Loom videos, YouTube links, and screenshots, then helps coding agents fix bugs, build features, and create skills.

## Install

```bash
# Add the plugin to Claude Code
/plugin marketplace add mnvsk97/eyeroll
/plugin install eyeroll@mnvsk97-eyeroll

# Install the CLI
pip install eyeroll[gemini]      # Gemini Flash API (recommended)
pip install eyeroll[openai]      # OpenAI GPT-4o
pip install eyeroll              # Ollama only (local, no API key)
pip install eyeroll[all]         # everything
```

## Setup

```
/eyeroll:init
```

Picks your backend, configures API key, and generates codebase context — all in one step.

## Commands

| Command | What it does |
|---------|-------------|
| `/eyeroll:init` | Set up eyeroll — pick backend, configure API key, generate `.eyeroll/context.md` |
| `/eyeroll:watch <url>` | Analyze a video and present a structured summary |
| `/eyeroll:fix <url>` | Watch a bug video → diagnose → fix the code → raise a PR |
| `/eyeroll:history` | List past video analyses |

## Usage

### In Claude Code

```
You: /eyeroll:watch https://loom.com/share/abc123
     → Analyzes video, presents: what's shown, the bug, key evidence, suggested fix

You: /eyeroll:fix https://loom.com/share/abc123
     → Watches video, greps codebase, finds the bug, fixes it, raises a PR

You: watch this tutorial and create a skill from it: ./demo.mp4
     → video-to-skill activates, watches video, generates SKILL.md

You: /eyeroll:history
     → Lists past analyses with timestamps and sources
```

### Standalone CLI

```bash
eyeroll watch https://loom.com/share/abc123
eyeroll watch ./bug.mp4 --context "checkout broken after PR #432"
eyeroll watch ./bug.mp4 -cc .eyeroll/context.md --parallel 4
eyeroll watch ./bug.mp4 --backend ollama -m qwen3-vl:2b
eyeroll history
```

## How it works

```
/eyeroll:watch https://loom.com/share/abc123
    ↓
1. Download video (yt-dlp)
    ↓
2. Extract frames (1 per 2s, deduplicate, enhance contrast)
    ↓
3. Analyze frames (Gemini / GPT-4o / Qwen3-VL)
   + transcribe audio if present
    ↓
4. Cache intermediates (reuse on next run)
    ↓
5. Synthesize report with codebase context:
   - Bug Description
   - Fix Directions (Visible / Codebase-informed / Hypothesis)
   - Search patterns for the coding agent
    ↓
6. Present summary to user
    ↓
/eyeroll:fix goes further:
   → grep codebase → read files → implement fix → run tests → PR
```

## Backends

| Backend | Video | Audio | API Key | Cost | Best for |
|---------|-------|-------|---------|------|----------|
| **gemini** | Direct upload | Yes | GEMINI_API_KEY | ~$0.15 | Best quality |
| **openai** | Frame-by-frame | Whisper | OPENAI_API_KEY | ~$0.20 | Existing OpenAI users |
| **ollama** | Frame-by-frame | No | None | Free | Privacy, offline |

Ollama auto-installs if not found (macOS/Linux).

## Codebase context

`/eyeroll:init` generates `.eyeroll/context.md` — a summary of your project that eyeroll uses to ground its analysis in real file paths instead of hallucinating them.

Without context, all file paths in the report are labeled as hypotheses.

## Caching

eyeroll caches frame analyses and transcripts in `.eyeroll/cache/`. Same video = no re-analysis. Different `--context` re-runs only the cheap synthesis step.

```bash
eyeroll watch video.mp4                    # full analysis (~15s)
eyeroll watch video.mp4 -c "new context"   # instant — cached frames
eyeroll watch video.mp4 --no-cache         # force fresh
```

## Plugin structure

```
eyeroll/
  commands/              ← slash commands
    init.md              ← /eyeroll:init
    watch.md             ← /eyeroll:watch
    fix.md               ← /eyeroll:fix
    history.md           ← /eyeroll:history
  skills/                ← background skills
    video-to-skill/      ← activated by "create a skill from this video"
  eyeroll/               ← Python CLI package
    cli.py, watch.py, analyze.py, extract.py, backend.py, history.py
  tests/                 ← 144 unit + 8 integration tests
```

## Supported inputs

| Input | Formats |
|-------|---------|
| **Video** | .mp4, .webm, .mov, .avi, .mkv, .flv, .ts, .m4v, .wmv, .3gp, .mpg, .mpeg |
| **Image** | .png, .jpg, .jpeg, .gif, .webp, .bmp, .tiff, .heic, .avif |
| **URL** | YouTube, Loom, Vimeo, Twitter/X, Reddit, 1000+ sites via yt-dlp |

## Development

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install -e '.[dev,all]'
pytest                                                    # unit tests
pytest tests/test_integration.py -v -m integration        # real API tests
```

## License

MIT
