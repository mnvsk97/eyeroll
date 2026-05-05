# /eyeroll:watch

Analyze a video, screen recording, or screenshot and produce a structured report.

## Usage

```
/eyeroll:watch <url-or-path> [--context "..."]
```

## What it does

1. Downloads the video (if URL) or reads the local file
2. Extracts key frames (1 per 2 seconds, deduplicated, contrast-enhanced)
3. Analyzes each frame with the configured vision model
4. Transcribes audio (if backend supports it and audio is present)
5. Checks cache for previous analysis of the same source
6. Synthesizes a structured report using codebase context

The agent then presents a concise summary rather than dumping the raw report.

## Arguments

| Argument | Description |
|---|---|
| `<url-or-path>` | Video URL (YouTube, Loom, etc.) or local file path |
| `--context "..."` | Additional context about the video (what it shows, what you want done) |
| `--no-context` | Skip auto-discovery of codebase context (CLAUDE.md, AGENTS.md, etc.) |
| `--no-cost` | Suppress cost estimate output |
| `--min-audio-confidence` | Minimum confidence for Whisper audio segments (0.0-1.0, default 0.4) |
| `--scene-threshold` | Pixel-diff threshold for scene-change frame extraction (default 30.0, 0=fixed interval) |

If you mention context in conversation without using the `--context` flag, the agent will pick it up and pass it along.

## Examples

```
/eyeroll:watch https://loom.com/share/abc123
/eyeroll:watch ./bug-recording.mp4
/eyeroll:watch ./screenshot.png --context "this error shows up on the settings page"
/eyeroll:watch https://youtube.com/watch?v=xyz --context "implement this feature"
```

## Report structure

The report first classifies the content type, then adapts its analysis sections accordingly.

### Content type detection

eyeroll determines what kind of content the video shows:

| Content Type | Example | Analysis Focus |
|---|---|---|
| **Bug report** | Error on screen, broken behavior | Expected vs actual, fix directions, search patterns |
| **Feature request** | Mockup or desired behavior | What's requested, implementation notes, acceptance criteria |
| **Question / answer request** | User asks how something works | Direct answer, evidence, follow-up questions |
| **Documentation lookup/update** | Docs are being read or requested | Relevant docs, missing docs, suggested update |
| **Tutorial** | Step-by-step how-to | Process, tools used, skill automation potential |
| **Code review** | PR diff walkthrough | Files reviewed, concerns noted |
| **Feature demo** | Working feature walkthrough | Capabilities shown, codebase relevance |
| **General notes** | Meeting, brainstorm | Key takeaways, action items |

### Report metadata

Every report starts with a structured metadata block:

```
intent: bug_report | feature_request | question_answering | documentation_lookup | documentation_update | tutorial_or_howto | code_review | feature_demo | product_feedback | general_notes
category: bug | feature | docs | question | other
confidence: high | medium | low
scope: in-context | out-of-context
repo_guess: <repo name or unknown>
repo_confidence: high | medium | low
severity: critical | moderate | low
actionable: yes | no
handoff_recommended: yes | no
```

- **intent**: specific content classification used to decide whether this is a bug, feature request, question, docs task, tutorial, review, or notes
- **category**: broad grouping used by older workflows
- **scope**: in-context if the video relates to the current codebase, out-of-context otherwise
- **repo_guess**: best repo match from provided codebase context, or `unknown` when unsure
- **actionable**: yes if a coding agent can take concrete action, no if informational only
- **handoff_recommended**: yes only when another coding agent should make code, docs, test, or config changes

### Common sections

Every report includes:

| Section | Content |
|---|---|
| **Metadata** | Intent, category, confidence, scope, repo guess, handoff recommendation |
| **Content Type** | Classification |
| **Summary** | One-sentence description of what the video shows |
| **What's Happening** | Step-by-step walkthrough |
| **Key Details** | Exact text from screen -- errors, URLs, status codes |
| **Audio/Narration** | What the person said (or "silent recording") |
| **Observations** | What works, what's broken, what's demonstrated |
| **Environment Clues** | Browser, OS, URLs, version numbers |
| **Analysis** | Adapted per content type (see above) |
| **Suggested Next Steps** | Context-aware recommendations |
| **Agent Handoff** | Included only when a code/docs/test/config change is recommended |
| **Clarifying Questions** | Only if something is genuinely unclear |

### Evidence confidence tiers (bug reports)

For bug reports, the Analysis section categorizes every claim:

- **Visible in recording** -- directly observed (error messages, URLs, UI state)
- **Informed by codebase context** -- references files from `.eyeroll/context.md`
- **Hypothesis (not confirmed)** -- educated guesses about root cause

This prevents the agent from hallucinating file paths or treating guesses as facts.

## Caching behavior

The same video analyzed with the same backend produces a cache hit. Only the synthesis step re-runs, using your new `--context`. This means:

```
/eyeroll:watch video.mp4                          # full analysis (~15s)
/eyeroll:watch video.mp4 --context "new angle"    # instant, cached frames
/eyeroll:watch video.mp4 --no-cache               # force fresh analysis
```

## CLI equivalent

```bash
eyeroll watch <source> [options]
```

See [CLI Reference](../cli.md) for all flags.
