# /eyeroll:fix

Watch a bug video, diagnose the issue, fix the code, and raise a PR -- all in one command.

## Usage

```
/eyeroll:fix <url-or-path> [--context "..."]
```

## What it does

`/eyeroll:fix` extends `/eyeroll:watch` with a full fix workflow:

1. **Analyze** -- runs `eyeroll watch` to produce a structured report
2. **Diagnose** -- extracts error messages, URLs, and search patterns from the report
3. **Search** -- greps the codebase using suggested patterns and reads identified files
4. **Fix** -- implements minimal, focused changes
5. **Test** -- runs the project's test suite; writes a test if one would catch the bug
6. **PR** -- creates a branch, commits, pushes, and opens a pull request

## Examples

```
/eyeroll:fix https://loom.com/share/abc123
/eyeroll:fix ./bug.mp4 --context "checkout broken after PR #432"
/eyeroll:fix ./screenshot.png --context "this 500 error started yesterday"
```

## Diagnosis flow

The agent extracts from the report:

- Exact error messages and status codes
- URLs and routes visible in the recording
- Search patterns from the Fix Directions section
- File references from codebase context

It then searches the codebase:

```bash
grep -r "TypeError: Cannot read properties" .
grep -r "stripe_id" .
```

If the context mentions a regression, it checks recent changes:

```bash
gh pr view 432
git log --since="1 week ago" -- src/checkout/
```

## PR format

The generated PR includes:

```markdown
## Summary
What was broken and why.

## Bug Evidence
- Video: <source URL>
- Error: <exact error message>

## Changes
- src/checkout/handler.py: Added null check for stripe_id

## Test Plan
- Verify checkout flow completes without error
```

## Confidence gates

The agent adjusts its behavior based on diagnosis confidence:

| Confidence | Behavior |
|---|---|
| **High** | Implements fix, opens PR |
| **Medium** | Implements fix, opens PR as **draft** |
| **Low** | Presents findings, asks before implementing |

!!! warning "Low confidence"
    When the video is ambiguous or the codebase context is missing, the agent will stop and ask for confirmation rather than making changes it is unsure about.
