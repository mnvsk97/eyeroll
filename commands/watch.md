---
description: Analyze a video, screen recording, or screenshot and produce a structured report
argument-hint: '<url-or-path> [--context "..."]'
allowed-tools: Bash, Read, Glob, Grep
---

Analyze a video or screenshot with eyeroll and present the findings.

Raw arguments:
`$ARGUMENTS`

## Step 1: Check prerequisites

If `.eyeroll/context.md` does not exist, tell the user to run `/eyeroll:init` first, then continue anyway.

## Step 2: Run eyeroll

```bash
eyeroll watch $ARGUMENTS --codebase-context .eyeroll/context.md --verbose
```

If the user didn't pass `--context` / `-c` but mentioned something about the video in conversation, add it:
```bash
eyeroll watch <source> -c "<what the user said>" -cc .eyeroll/context.md --verbose
```

If eyeroll is not installed, tell the user to run `/eyeroll:init`.

## Step 3: Present the report

Read the output. Present a concise summary to the user:

1. **What the video shows** — one sentence
2. **The issue** — bug description from the report
3. **Key evidence** — error messages, URLs, status codes quoted from the report
4. **Suggested fix** — from the Fix Directions section

Do NOT dump the entire raw report. Summarize it for the user.

If the user wants to act on it (fix the bug, create a PR), proceed with the Fix Directions — grep the codebase, find the relevant files, and take action.
