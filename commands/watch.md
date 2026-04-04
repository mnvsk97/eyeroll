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

Read the output. Look at the **Content Type** detected in the report and present accordingly:

**For bug reports:**
1. **What the video shows** — one sentence
2. **The bug** — expected vs actual behavior
3. **Key evidence** — error messages, URLs, status codes quoted from the report
4. **Suggested fix** — from the Analysis section
5. Offer: "Want me to fix this? I can investigate and raise a PR with `/eyeroll:fix`."

**For tutorials/how-tos:**
1. **What the video teaches** — one sentence
2. **Key steps** — the workflow demonstrated
3. **Tools/commands used**
4. Offer: "Want me to turn this into a reusable skill? I can create one with the video-to-skill workflow."

**For feature demos:**
1. **What's being demonstrated** — one sentence
2. **Key capabilities shown**
3. **How it relates to the codebase** (if context available)

**For feature requests:**
1. **What's being requested** — one sentence
2. **Desired behavior** vs current behavior
3. Offer: "Want me to spec this out or start building it?"

**For any other content:**
1. **What the video shows** — one sentence
2. **Key takeaways** from the report
3. **Suggested next steps** from the report

Do NOT dump the entire raw report. Summarize it for the user.
Suggest the most relevant next action based on content type.
