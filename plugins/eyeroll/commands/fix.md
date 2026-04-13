---
description: Watch a bug video, diagnose the issue, fix the code, and raise a PR
argument-hint: '<url-or-path> [--context "..."]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Watch a video showing a bug, diagnose it, fix the code, and raise a PR.

Raw arguments:
`$ARGUMENTS`

## Step 1: Check prerequisites

If `.eyeroll/context.md` does not exist, tell the user to run `/eyeroll:init` first, then continue anyway.

## Step 2: Analyze the video

```bash
eyeroll watch $ARGUMENTS --codebase-context .eyeroll/context.md --verbose
```

If the user mentioned context in conversation, add `-c "<their words>"`.

## Step 3: Triage

Read the report. Check the **Metadata** block first:
- If **scope is out-of-context**, warn the user — the video doesn't relate to this codebase
- If **actionable is no**, tell the user — there's nothing concrete to fix here
- If **category is not bug**, note this — the fix command is designed for bugs

Check **severity** to set urgency expectations (critical/moderate/low).

## Step 4: Diagnose

Read the report. Extract:
- **Reproduction steps** (from the dedicated section)
- Error messages (exact text)
- URLs and routes visible
- Fix directions (search patterns, hypotheses)

Search the codebase using the suggested patterns with `Grep` and `Glob` tools. Cross-reference with the video observations.

If context mentions a regression ("after PR #X", "since last deploy"):
```bash
gh pr view <number>
git log --since="1 week ago" -- <identified-files>
```

## Step 5: Fix

Implement the fix. Keep changes minimal and focused.

## Step 6: Test

Run the project's test suite. If a test would have caught this bug, write one.

## Step 7: PR

Create a branch, commit, push, and open a PR:

```bash
gh pr create --title "Fix: <brief description>" --body "$(cat <<'EOF'
## Summary
<what was broken and why>

## Bug Evidence
- Video: <source URL if available>
- Error: <exact error message>

## Changes
- <file>: <what changed>

## Test Plan
- <how to verify>
EOF
)"
```

If diagnosis confidence is low, present findings and ask the user before implementing.
Create the PR as a draft if confidence is medium or lower.
