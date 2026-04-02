---
name: history
description: >
  List past video analyses from the eyeroll cache. Use to reference
  previous reports, compare findings across sessions, or clear stale data.
compatibility: "Requires eyeroll installed"
---

# History

View and manage past eyeroll video analyses.

## What This Skill Does

Lists cached analysis reports so you can reference previous findings, compare across sessions, or clean up stale data.

## Commands

```bash
# List all past analyses (newest first)
eyeroll history

# Show only the last 10
eyeroll history --limit 10

# JSON output for programmatic use
eyeroll history --json

# Clear all cached analyses
eyeroll history clear
eyeroll history clear --yes   # skip confirmation
```

## When To Use This Skill

- User asks "what videos have I analyzed before?"
- User references a past analysis: "this looks like the same bug from the Jan 15 analysis"
- User wants to compare current findings with a previous report
- User wants to clean up or reset the cache
- Before re-analyzing a video, check if a cached report already exists

## Workflow

### Referencing past analyses

1. Run `eyeroll history` to see what has been analyzed
2. Use the cache key from the output to find the cached report in `.eyeroll/cache/{key}.md`
3. Read the report and compare with current findings

### Clearing stale cache

1. Run `eyeroll history` to review what is cached
2. Run `eyeroll history clear` to remove all cached data
3. Re-run `eyeroll watch` for fresh analysis

## Rules

- The cache lives in `.eyeroll/cache/` relative to the working directory.
- Each entry has a `.json` metadata file and a `.md` report file.
- Older cache entries may lack `title` and `media_type` fields -- this is normal.
- Use `--json` output when you need to parse the history programmatically.
