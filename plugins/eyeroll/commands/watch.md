---
description: Analyze a video, screen recording, or screenshot and produce a structured report
argument-hint: '<url-or-path> [--context "..."]'
allowed-tools: Bash, Read, Glob, Grep
---

Analyze a video or screenshot with eyeroll and present the findings.

Raw arguments:
`$ARGUMENTS`

## Step 1: Run eyeroll

Codebase context is auto-discovered from CLAUDE.md, AGENTS.md, .cursorrules, etc.

```bash
eyeroll watch $ARGUMENTS --verbose
```

If the user didn't pass `--context` / `-c` but mentioned something about the video in conversation, add it:
```bash
eyeroll watch <source> -c "<what the user said>" --verbose
```

If eyeroll is not installed, tell the user to run `/eyeroll:init`.

## Step 2: Present the report

Read the output. First, check the **Metadata** block at the top for quick triage:

- **category** (bug/feature/other), **confidence**, **scope** (in-context/out-of-context), **severity**, **actionable**

If **scope is out-of-context** or **actionable is no**, note this to the user — the video isn't related to the current codebase.

Then look at the **Content Type** and present accordingly:

**For bug reports:**
1. Metadata summary — category, severity, scope, actionable (one line)
2. **What the video shows** — one sentence
3. **The bug** — expected vs actual behavior
4. **Reproduction steps** — from the report
5. **Key evidence** — error messages, URLs, status codes quoted from the report
6. **Suggested fix** — from the Analysis section
7. Offer: "Want me to fix this? I can investigate and raise a PR with `/eyeroll:fix`."

**For tutorials/how-tos:**
1. Metadata summary (one line)
2. **What the video teaches** — one sentence
3. **Key steps** — the workflow demonstrated
4. **Tools/commands used**
5. Offer: "Want me to turn this into a reusable skill? I can create one with the video-to-skill workflow."

**For feature demos:**
1. Metadata summary (one line)
2. **What's being demonstrated** — one sentence
3. **Key capabilities shown**
4. **How it relates to the codebase** (if context available)

**For feature requests:**
1. Metadata summary (one line)
2. **What's being requested** — one sentence
3. **Desired behavior** vs current behavior
4. Offer: "Want me to spec this out or start building it?"

**For any other content:**
1. Metadata summary (one line)
2. **What the video shows** — one sentence
3. **Key takeaways** from the report
4. **Suggested next steps** from the report

Do NOT dump the entire raw report. Summarize it for the user.
Suggest the most relevant next action based on content type.
