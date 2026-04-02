---
name: video-to-pr
description: >
  Watch a bug video, screen recording, or screenshot, understand what's broken,
  find the relevant code, implement a fix, and raise a PR. Supports Loom,
  YouTube, and local files. Uses Gemini Flash for video understanding.
---

# Video to PR

Watch a bug video or screenshot, diagnose the issue, find the relevant code, fix it, and raise a pull request.

## What This Skill Does

Given a video showing a bug (Loom, YouTube, local file, screenshot), this skill:

1. Analyzes the video to understand what's broken (via `eyeroll watch`)
2. Extracts error messages, URLs, UI state, and user actions
3. Searches the codebase for relevant files (route mapping, error grep, component matching)
4. Diagnoses the root cause
5. Implements the fix
6. Writes a test if applicable
7. Raises a PR with full context linking back to the original video

## Setup

```bash
pip install eyeroll
eyeroll init          # set up Gemini API key
brew install yt-dlp   # for URL downloads
```

Or: `export GEMINI_API_KEY=your-key`

## When To Use This Skill

- User shares a bug video and says "fix this" or "raise a PR"
- User pastes a Loom/YouTube link showing broken behavior and wants it fixed
- User says "watch this and fix it", "create a PR for this bug"
- User shares a screenshot of an error and wants it resolved
- QA or customer sends a recording of a bug

## Workflow

```
1. Check for .eyeroll/context.md (if missing, suggest /eyeroll:init)

2. Run: eyeroll watch <source> \
     --context "user's description" \
     --codebase-context .eyeroll/context.md \
     --verbose

3. Read the report — extract:
   - Bug description (expected vs actual)
   - Error messages and URLs visible in recording
   - Fix Directions (what's confirmed vs hypothesized)

4. Search the codebase using the report's suggested search patterns:
   - Route/URL visible → match to routing config → find page/handler
   - Error message visible → grep for exact string
   - Component/page name → find source file

5. Read the identified files. Cross-reference with video observations.

6. If context mentions regression ("after PR #X", "since last deploy"):
   - gh pr view <number> to understand what changed
   - git log --since="1 week ago" -- <identified-files>

7. Implement the fix

8. Write a test that would have caught the bug

9. Create branch, commit, push, open PR
```

## Example Interactions

User: "Fix this bug: https://loom.com/share/abc123"
Steps:
1. Check for `.eyeroll/context.md`
2. `eyeroll watch https://loom.com/share/abc123 -cc .eyeroll/context.md`
3. Report shows: 500 error on /api/payments, "billingAddress is undefined"
4. Grep for "billingAddress" → find relevant files
5. Read files, diagnose, fix, write test, raise PR

User: "Checkout is broken after PR #432, here's a recording" [video.mp4]
Steps:
1. `eyeroll watch video.mp4 -c "broken after PR #432" -cc .eyeroll/context.md`
2. `gh pr view 432` to understand what changed
3. Cross-reference report findings with PR #432 diff
4. Fix, test, PR

## Rules

- Check for `.eyeroll/context.md` first. If missing, suggest `/eyeroll:init`.
- Do NOT guess what files to change based on the video alone — always search the codebase.
- Include the video URL (if available) in the PR description for traceability.
- If diagnosis confidence is low, present findings and ask the user before implementing a fix.
- If the fix spans multiple files, explain the full scope before making changes.
- Write a test when feasible. At minimum, ensure existing tests still pass.
- Create the PR as a draft if confidence is medium or lower.

## PR Template

```markdown
## Summary
Fix [brief description of the bug]

## Root Cause
[What was wrong and why]

## Bug Evidence
- Video: [link to original video if URL]
- Error: [exact error message from video]
- Affected page: [URL/route from video]

## Changes
- [file1]: [what changed and why]
- [file2]: [what changed and why]

## Test Plan
- [how to verify the fix]
```
