# CLI Reference

The `eyeroll` CLI provides direct access to video analysis without Claude Code.

## Commands

### `eyeroll init`

Set up eyeroll -- choose a backend and configure API key.

```bash
eyeroll init
```

Interactive. Saves configuration to `~/.eyeroll/.env`.

---

### `eyeroll watch`

Analyze a video or screenshot and produce structured notes.

```bash
eyeroll watch <source> [options]
```

**Arguments:**

| Argument | Description |
|---|---|
| `source` | URL (YouTube, Loom, etc.) or local file path |

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--context` | `-c` | None | Additional context text |
| `--codebase-context` | `-cc` | None | Codebase context (inline text or path to file) |
| `--backend` | `-b` | `EYEROLL_BACKEND` or `gemini` | Backend: `gemini`, `openai`, or `ollama` |
| `--model` | `-m` | Backend default | Model override |
| `--max-frames` | | 20 | Maximum key frames to analyze |
| `--parallel` | `-p` | 3 (API) / 1 (ollama) | Concurrent workers for frame analysis |
| `--no-cache` | | false | Skip cache, force fresh analysis |
| `--output` | `-o` | stdout | Write report to file |
| `--verbose` | `-v` | false | Show progress details |

**Examples:**

```bash
# Basic usage
eyeroll watch https://loom.com/share/abc123

# With context
eyeroll watch ./bug.mp4 --context "checkout broken after PR #432"

# With codebase context file
eyeroll watch ./bug.mp4 -cc .eyeroll/context.md

# Parallel frame analysis
eyeroll watch ./bug.mp4 -p 4 --verbose

# Use Ollama with a specific model
eyeroll watch ./demo.mp4 -b ollama -m qwen3-vl:2b

# Write report to file
eyeroll watch ./bug.mp4 -o report.md

# Force fresh analysis (skip cache)
eyeroll watch ./bug.mp4 --no-cache
```

!!! note "Model inference"
    If you pass `--model` without `--backend`, eyeroll infers the backend from the model name. Models starting with `gemini` use the Gemini backend. Models starting with `gpt`, `o1`, or `o3` use OpenAI. All others default to Ollama.

---

### `eyeroll history`

List past analyses from the cache.

```bash
eyeroll history [options]
```

**Options:**

| Flag | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-n` | All | Show only the last N entries |
| `--json` | | false | Output as JSON |

**Examples:**

```bash
eyeroll history
eyeroll history --limit 5
eyeroll history --json
```

---

### `eyeroll history clear`

Clear all cached analyses.

```bash
eyeroll history clear [options]
```

**Options:**

| Flag | Short | Description |
|---|---|---|
| `--yes` | `-y` | Skip confirmation prompt |

**Examples:**

```bash
eyeroll history clear
eyeroll history clear --yes
```

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `EYEROLL_BACKEND` | Default backend | `gemini` |
| `GEMINI_API_KEY` | Gemini API key | |
| `OPENAI_API_KEY` | OpenAI API key | |
| `OLLAMA_HOST` | Ollama server address | `http://localhost:11434` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google service account JSON | |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID (for service account) | |
| `GOOGLE_CLOUD_LOCATION` | Google Cloud region (for service account) | `us-central1` |

eyeroll loads environment variables from `~/.eyeroll/.env` and the project's `.env` file.
