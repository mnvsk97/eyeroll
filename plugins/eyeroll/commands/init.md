---
description: Set up eyeroll for this project — pick a backend, install dependencies, and generate codebase context
argument-hint: ''
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion
---

Set up eyeroll for the current project.

## Step 1: Check if eyeroll is installed

```bash
eyeroll --help
```

If not found, ask the user which backend they want:

Use `AskUserQuestion` with these options:
- `Gemini (Recommended)` — Google Gemini Flash API, best quality, requires API key or credentials.json
- `OpenAI` — GPT-4o, requires API key
- `Ollama` — Local models, private, no API key needed

Then install:
- Gemini: `pip install eyeroll[gemini]`
- OpenAI: `pip install eyeroll[openai]`
- Ollama: `pip install eyeroll`

## Step 2: Run eyeroll init

```bash
eyeroll init
```

This is interactive — it asks for the backend choice and API key. Let the user interact with it directly.

## Step 3: Generate codebase context

After setup, explore the codebase and write `.eyeroll/context.md`:

1. Read `CLAUDE.md`, `README.md`, `pyproject.toml` or `package.json`
2. Run `git log --oneline -10` and `git branch --show-current`
3. Run `ls` on root and key source directories
4. Skim 2-3 key source files

Write `.eyeroll/context.md` with this structure — keep it under 80 lines:

```markdown
# Project: <name>
## Stack
<language, framework, key libraries>
## Structure
<directory layout>
## Key Files
- <file>: <purpose>
## Recent Activity
<last 5-10 commits, current branch>
## Notes
<anything relevant — conventions, known issues>
```

## Step 4: Confirm

Tell the user:
- eyeroll is ready
- `.eyeroll/context.md` has been generated
- They can run `/eyeroll:watch <video>` to analyze a video
