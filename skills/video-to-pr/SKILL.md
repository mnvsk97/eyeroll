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
1. Run: eyeroll watch <source> --context "..." --verbose
2. Read the structured notes — extract error messages, URLs, affected pages
3. Search the codebase:
   - Route/URL visible → match to routing config → find page/handler files
   - Error message visible → grep codebase for exact string
   - Component/page name → find source file
   - API endpoint → find handler
4. Read the identified files
5. Diagnose: cross-reference video observations with code
6. If context mentions regression ("after PR #X", "since last deploy"):
   - Check recent git history for the relevant files
   - git log --since="1 week ago" -- <identified-files>
7. Implement the fix
8. Write a test that would have caught the bug
9. Create branch, commit, push, open PR with:
   - Link to original video (if URL)
   - Summary of what was broken and why
   - What was fixed
```

## Example Interactions

User: "Fix this bug: https://loom.com/share/abc123"
Steps:
1. `eyeroll watch https://loom.com/share/abc123`
2. Notes show: 500 error on /api/payments, "billingAddress is undefined"
3. Grep for "billingAddress" → find `src/pages/checkout.tsx` and `api/payments.py`
4. Read files, diagnose: field was renamed in migration but not updated in frontend
5. Fix both files, write test, raise PR

User: "Checkout is broken after PR #432, here's a recording" [video.mp4]
Steps:
1. `eyeroll watch video.mp4 --context "broken after PR #432"`
2. Notes show the error + context points to PR #432
3. `gh pr view 432` to understand what changed
4. Cross-reference changes with the error
5. Fix, test, PR

## Rules

- Always run `eyeroll watch` first to get structured notes before touching code.
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
