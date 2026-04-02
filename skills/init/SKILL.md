---
name: init
description: >
  Set up eyeroll for the current project. Ensures API key is configured,
  explores the codebase, and generates .eyeroll/context.md so future
  video analyses are grounded in real project context.
---

# Init

Set up eyeroll for the current project so video analysis is grounded in codebase context.

## What This Skill Does

1. Runs `eyeroll init` — asks user to pick a backend (Gemini, OpenAI, or Ollama) and set up API key
2. Installs the right extras if needed (`pip install eyeroll[gemini]` or `eyeroll[openai]`)
3. Explores the codebase to understand the project
4. Writes `.eyeroll/context.md` — a concise summary that gets passed to eyeroll during video analysis

## Workflow

### Step 1: Check prerequisites

```bash
eyeroll --help
```

If not installed: `pip install eyeroll`

Check if GEMINI_API_KEY is set:
```bash
echo $GEMINI_API_KEY
```

If not set, run `eyeroll init` to configure it interactively.

### Step 2: Explore the codebase

Read these files (skip any that don't exist):

1. `CLAUDE.md` — project instructions and architecture
2. `README.md` or `README.rst` — project overview
3. `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` — dependencies and project name
4. Run `git log --oneline -10` — recent changes
5. Run `git branch --show-current` — active branch
6. Run `ls` on the project root and key source directories
7. Skim 2-3 key source files (entry points, main modules)

### Step 3: Write `.eyeroll/context.md`

Create `.eyeroll/context.md` with this structure:

```markdown
# Project: <name>

## Stack
<language>, <framework>, <key libraries>

## Structure
<brief description of directory layout and key directories>

## Key Files
- <file>: <what it does>
- <file>: <what it does>
- ...

## Recent Activity
<last 5-10 commits, current branch, any in-progress work>

## Notes
<anything else relevant — deployment setup, known issues, conventions>
```

Keep it under 80 lines. Be concise. This will be injected into video analysis prompts, so every line should help the AI understand bug reports better.

### Step 4: Confirm

Tell the user:
- eyeroll is ready
- `.eyeroll/context.md` has been generated
- They can edit it to add project-specific notes
- Run `/eyeroll:watch <video>` to analyze a video with full codebase context

## When To Use This Skill

- User says "set up eyeroll", "eyeroll init", "initialize eyeroll"
- First time using eyeroll in a project
- User wants to regenerate codebase context
- User says "update eyeroll context"

## Rules

- Do NOT run `eyeroll watch` in this skill — this is setup only.
- Keep `.eyeroll/context.md` concise. It's a prompt input, not documentation.
- If CLAUDE.md exists, use it as the primary source of truth for project understanding.
- Create the `.eyeroll/` directory if it doesn't exist.
- If `.eyeroll/context.md` already exists, ask the user before overwriting.
