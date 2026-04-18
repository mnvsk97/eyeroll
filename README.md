# eyeroll

[![CI](https://github.com/mnvsk97/eyeroll/actions/workflows/ci.yml/badge.svg)](https://github.com/mnvsk97/eyeroll/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/eyeroll)](https://pypi.org/project/eyeroll/)
[![Python](https://img.shields.io/pypi/pyversions/eyeroll)](https://pypi.org/project/eyeroll/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI eyes that roll through video footage — watch, understand, act.

eyeroll is a Claude Code plugin that analyzes screen recordings, Loom videos, YouTube links, and screenshots, then helps coding agents fix bugs, build features, and create skills.

## Install

```bash
# Add the plugin to Claude Code
/plugin marketplace add mnvsk97/eyeroll
/plugin install eyeroll@mnvsk97-eyeroll

# Install the CLI
pip install eyeroll[gemini]      # Gemini Flash API (recommended)
pip install eyeroll[openai]      # OpenAI GPT-4o + OpenRouter/Groq/Grok/Cerebras
pip install eyeroll              # Ollama only (local, no API key) — requires Pillow
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
eyeroll watch ./bug.mp4 --backend groq
eyeroll watch ./bug.mp4 --backend openrouter -m anthropic/claude-3.5-sonnet
eyeroll watch ./bug.mp4 --backend openai-compat --base-url https://my-server/v1
eyeroll watch ./bug.mp4 --no-context               # skip auto-discovery of codebase context
eyeroll watch ./bug.mp4 --no-cost                   # suppress cost estimate
eyeroll watch ./bug.mp4 --scene-threshold 50        # tune scene-change sensitivity
eyeroll watch ./bug.mp4 --min-audio-confidence 0.6  # stricter audio filtering
eyeroll history
```

## How it works

```
/eyeroll:watch https://loom.com/share/abc123
    ↓
1. Preflight check (verify backend is reachable, detect capabilities)
    ↓
2. Download video (yt-dlp)
    ↓
3. Choose strategy:
   - Gemini API key: direct upload via File API (up to 2GB)
   - Gemini service account: direct upload (up to 20MB)
   - OpenAI / OpenRouter / Groq: multi-frame batch (all frames in one call)
   - Ollama: frame-by-frame (one frame per call)
    ↓
4. Transcribe audio if present
    ↓
5. Cache intermediates (reuse on next run)
    ↓
6. Synthesize report with codebase context:
   - Metadata: category, confidence, scope, severity, actionable
   - Bug Description + Reproduction Steps
   - Fix Directions (Visible / Codebase-informed / Hypothesis)
   - Search patterns for the coding agent
    ↓
7. Present summary to user
    ↓
/eyeroll:fix goes further:
   → grep codebase → read files → implement fix → run tests → PR
```

## Backends

| Backend | Strategy | Audio | API Key | Cost | Best for |
|---------|----------|-------|---------|------|----------|
| **gemini** | Direct upload (up to 2GB) | Yes | GEMINI_API_KEY | ~$0.15 | Best quality (gemini-2.5-flash) |
| **openai** | Multi-frame batch | Whisper | OPENAI_API_KEY | ~$0.20 | Existing OpenAI users |
| **ollama** | Frame-by-frame | No | None | Free | Privacy, offline |
| **openrouter** | Multi-frame batch | No | OPENROUTER_API_KEY | varies | Model variety |
| **groq** | Multi-frame batch | No | GROQ_API_KEY | cheap | Low latency |
| **grok** | Multi-frame batch | No | GROK_API_KEY | varies | xAI models |
| **cerebras** | Multi-frame batch | No | CEREBRAS_API_KEY | cheap | Fast inference |
| **openai-compat** | Multi-frame batch | No | any env var | varies | Custom/self-hosted endpoints |

Ollama auto-installs if not found (macOS/Linux).

## Codebase context

eyeroll automatically discovers codebase context from files like `CLAUDE.md`, `AGENTS.md`, `CURSOR.md`, and `.eyeroll/context.md` (disable with `--no-context`). You can also run `/eyeroll:init` to generate `.eyeroll/context.md` manually.

Without context, all file paths in the report are labeled as hypotheses.

## Caching

eyeroll caches frame analyses and transcripts in `~/.eyeroll/cache/` (global). Same video = no re-analysis. Different `--context` re-runs only the cheap synthesis step. Legacy local `.eyeroll/cache/` is still checked for backward compatibility.

```bash
eyeroll watch video.mp4                    # full analysis (~15s)
eyeroll watch video.mp4 -c "new context"   # instant — cached frames
eyeroll watch video.mp4 --no-cache         # force fresh
```

## Cost estimates

eyeroll prints a cost estimate to stderr after each analysis. Disable with `--no-cost`. Ollama runs are always free.

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
    cli.py, watch.py, analyze.py, extract.py, backend.py, context.py, cost.py, history.py
  tests/                 ← 269 unit + 8 integration tests
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
