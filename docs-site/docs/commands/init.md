# /eyeroll:init

Set up eyeroll for the current project -- pick a backend, install dependencies, and generate codebase context.

## Usage

```
/eyeroll:init
```

No arguments needed.

## What it does

### Step 1: Check installation

Checks if `eyeroll` CLI is installed. If not, asks which backend you want and installs the appropriate package:

| Choice | Install command |
|---|---|
| Gemini | `pip install eyeroll[gemini,download]` |
| OpenAI | `pip install eyeroll[openai,download]` |
| Ollama | `pip install eyeroll[download]` |

### Step 2: Configure backend

Runs `eyeroll init` interactively:

- Prompts for backend choice (Gemini, OpenAI, Ollama)
- For Gemini/OpenAI: prompts for API key and validates it
- For Ollama: verifies Ollama is running (or starts it)
- Saves configuration to `~/.eyeroll/.env`

### Step 3: Generate codebase context

Explores the project and writes `.eyeroll/context.md`:

1. Reads `CLAUDE.md`, `README.md`, `pyproject.toml` or `package.json`
2. Checks `git log --oneline -10` and current branch
3. Lists root and key source directories
4. Skims 2-3 key source files

The resulting file is a short summary (under 80 lines) that eyeroll uses to ground its analysis in real file paths.

## What gets created

| File | Location | Purpose |
|---|---|---|
| `.env` | `~/.eyeroll/.env` | Backend preference and API key |
| `context.md` | `.eyeroll/context.md` | Project summary for grounded analysis |

## When to re-run

Re-run `/eyeroll:init` when:

- You want to switch backends
- Your API key has changed
- The project structure has changed significantly (major refactor, new directories)

The codebase context file is what makes the difference between vague guesses and precise file references in eyeroll reports.
