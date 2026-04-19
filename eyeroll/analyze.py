"""Analyze video frames and audio to produce structured notes."""

import os
import sys

from .backend import get_backend

FRAME_ANALYSIS_PROMPT = """You are analyzing a screen recording.
This is frame {frame_index} at timestamp {timestamp}.

Look at this screenshot carefully and extract:

1. **PAGE/URL**: What page, URL, or route is visible? (check address bar, breadcrumbs, page title)
2. **UI STATE**: What UI elements are visible? (forms, buttons, modals, tables, navigation, code editors, terminals)
3. **TEXT ON SCREEN**: All significant text — error messages, labels, headings, code, terminal output, URLs. Quote exact wording.
4. **ERRORS/WARNINGS**: Any error messages, red text, warning banners, toast notifications, console errors?
5. **USER ACTION**: Any indication of what the user just did or is about to do? (cursor position, active element, form state)
6. **WHAT'S BEING SHOWN**: What is the person demonstrating or pointing out?

Be precise. Quote exact text from the screen. If you can't read something clearly, say so.
Do NOT hallucinate or guess text you can't see clearly."""

VIDEO_ANALYSIS_PROMPT = """You are analyzing a screen recording.
The video is {duration} seconds long.

Watch the entire video carefully and describe:

1. **STEPS**: What is the user doing step by step? (navigating, clicking, typing, scrolling, demonstrating)
2. **PAGES/URLS**: What pages, routes, or applications are shown?
3. **TEXT ON SCREEN**: Exact text visible — error messages, status codes, console output, code, labels, URLs.
4. **ERRORS/ISSUES**: Any error messages, failed requests, broken UI, unexpected behavior?
5. **WHAT'S BEING DEMONSTRATED**: What is the person showing or explaining? Is this a bug, a feature demo, a tutorial, a walkthrough?
6. **KEY MOMENTS**: What are the most important moments or transitions in the video?

Be precise. Quote exact text. Don't guess what you can't see clearly."""

BATCH_FRAMES_PROMPT = """You are analyzing a screen recording. The frames below are key moments extracted from the video, shown in chronological order with timestamps.

For each frame, extract:
1. **PAGE/URL**: What page, URL, or route is visible?
2. **UI STATE**: What UI elements are visible?
3. **TEXT ON SCREEN**: All significant text — error messages, labels, code, URLs. Quote exact wording.
4. **ERRORS/WARNINGS**: Any error messages, red text, warnings?
5. **USER ACTION**: What the user just did or is about to do
6. **WHAT'S BEING SHOWN**: What is being demonstrated

Then provide an overall narrative of what happens across all frames.
Be precise. Quote exact text. If you can't read something clearly, say so."""

AUDIO_PROMPT = (
    "Transcribe this audio from a video recording. "
    "Include everything the speaker says. "
    "Note any references to specific features, pages, errors, or timeframes. "
    "If the audio is silent or contains no speech, respond with: [no speech detected]"
)

SYNTHESIS_PROMPT = """You are a senior developer analyzing a screen recording or screenshot.

Here are the raw observations from the video:

## Frame-by-frame analysis:
{frame_analyses}

## Additional context from the person who shared this:
{context}

## Audio transcript (if available):
{transcript}

## Codebase context (project structure, tech stack, key files):
{codebase_context}

---

First, determine what KIND of content this is based on the visual evidence, audio, and context:
- **Bug report**: shows broken behavior, errors, unexpected results
- **Feature demo**: demonstrates working functionality, a new feature, or a product walkthrough
- **Tutorial/how-to**: teaches a process or workflow step by step
- **Feature request**: shows desired behavior or a mockup/design
- **Code review**: walks through code changes or PR diffs
- **General notes**: anything else (meeting recording, brainstorm, etc.)

Then synthesize into structured, actionable notes. Output EXACTLY this format:

## Video Analysis

### Metadata
```
category: [bug | feature | other]
confidence: [high | medium | low]
scope: [in-context | out-of-context]
severity: [critical | moderate | low]
actionable: [yes | no]
```

Rules for metadata:
- **category**: "bug" for bug reports, "feature" for feature demos/requests/tutorials, "other" for everything else
- **confidence**: how confident you are in your analysis
- **scope**: "in-context" if the video relates to the codebase described in the codebase context section, "out-of-context" if unrelated or no codebase context provided
- **severity**: "critical" for crashes/data loss/security issues, "moderate" for broken features/errors, "low" for cosmetic/minor issues. For non-bugs, base on importance.
- **actionable**: "yes" if a coding agent can take concrete action (fix a bug, build a feature, create a skill), "no" if it's just informational

### Content Type: [bug report | feature demo | tutorial | feature request | code review | general notes]
State what kind of content this is.

### Summary
One or two sentences describing what this video shows.

### What's Happening (step by step)
1. Step one
2. Step two
3. ...

### Key Details
- Exact text visible on screen (error messages, URLs, labels, code — quote verbatim)
- UI elements and their state
- HTTP status codes, console output, network requests if visible
- Any configuration, settings, or environment info visible

### Audio/Narration Summary
What the person said (key points only). Or "(silent recording)" if no audio.

### Observations
- What appears to be working
- What appears to be broken or unexpected
- What was demonstrated or explained

### Environment Clues
- Browser/OS if visible
- URLs, routes, deployment info
- Any version numbers visible

### Confidence: [high/medium/low]
State your confidence and explain what's clear vs ambiguous.

### Analysis
<!-- Adapt this section based on content type -->

**If bug report:**

### Reproduction Steps
Distill the minimal steps to reproduce this bug from the video:
1. Step one
2. Step two
3. ...
(Only include this section for bugs. Keep it minimal — just enough to trigger the issue.)

- What is the expected behavior vs. the actual behavior?
- What triggers the issue?
- Categorize evidence:
  - **Visible in recording**: directly observed errors, URLs, UI state (quote exact text)
  - **Informed by codebase context**: only reference files from the codebase context section
  - **Hypothesis (not confirmed)**: educated guesses, clearly labeled
- Suggested search patterns for the coding agent
- How to fix (concrete steps, reference actual project files when context is available)
- How to verify the fix

**If feature demo:**
- What feature or workflow is being demonstrated?
- Key capabilities shown
- How it relates to the codebase (if context is available)

**If tutorial/how-to:**
- What process or workflow is being taught?
- Tools and commands used (list them)
- Key steps to reproduce the workflow
- Could this be turned into an automated skill or script?

**If feature request:**
- What is being requested or proposed?
- What does the desired behavior look like?
- How does it differ from current behavior (if visible)?

**If code review:**
- What files/functions are being reviewed?
- Key changes discussed
- Concerns or approvals noted

**If general notes:**
- Key points and takeaways
- Action items mentioned

### Suggested Next Steps
Based on content type, suggest the most appropriate actions:
- Bug report → investigate and fix the code, raise a PR
- Feature demo → document it, create notes for the team
- Tutorial → create a reusable skill or automation from it
- Feature request → spec it out, create implementation tasks
- Code review → address feedback, update the PR
- General → summarize and share with relevant people

### Clarifying Questions
List any questions that would help understand what was shown better.
Only include if something is genuinely unclear — don't pad with generic questions.

---

Rules:
- Only include information you can actually see or hear in the recording
- Quote text from the screen EXACTLY — don't paraphrase
- If you're unsure about something, say "unclear" rather than guessing
- If the context text adds useful information, incorporate it
- Do NOT assume this is a bug — determine content type from evidence first
- Keep it concise and actionable
- NEVER state a file path as fact unless it appears in the codebase context section. If no codebase context is available, ALL file paths are hypotheses — say so explicitly.
- This report will be read by a coding agent, not a human. Be precise and codebase-oriented when relevant, but don't force technical analysis on non-technical content."""

SYNTHESIS_PROMPT_QUICK = """You are analyzing a screen recording or screenshot. Describe what you see directly and concisely.

Raw observations:

{frame_analyses}

{context}

Output EXACTLY this format:

## What's Shown
One or two sentences describing what this recording shows.

## Key Details
- Exact text visible (error messages, URLs, labels, code — quote verbatim)
- UI elements and their state
- Notable actions or transitions

## Interpretation
What is most likely happening or being demonstrated?

Rules:
- Only describe what you can actually see
- Quote exact text from the screen — do not paraphrase
- No elaborate analysis — keep it brief and direct"""

SYNTHESIS_PROMPT_MINIMAL = """You are a developer analyzing a screen recording or screenshot.

Raw observations:

{frame_analyses}

Context: {context}
Codebase: {codebase_context}

Output EXACTLY this format:

### Metadata
```
category: [bug | feature | other]
confidence: [high | medium | low]
actionable: [yes | no]
```

### Summary
One or two sentences.

### Key Details
- Exact text visible (quote verbatim)
- Errors, URLs, status codes, relevant UI state

### Next Steps
- Concrete action items only (3–5 max)

Rules: quote text exactly, no padding, no generic questions."""

SYNTHESIS_PROMPT_PR = """You are analyzing a screen recording or screenshot to produce a GitHub pull request description.

Raw observations:

{frame_analyses}

Context: {context}
Codebase: {codebase_context}

Based on what you see, write a GitHub PR description as if this recording documents the changes being made or requested.

Output EXACTLY this format:

## [PR Title]
Write a concise PR title (under 72 characters) describing the change.

## Summary
2–3 sentences explaining what this PR does and why.

## Changes
- Specific changes visible in the recording (bullet list)
- Quote exact text, error messages, or UI changes seen

## Why
What problem does this solve or what does it enable?

## Testing
- [ ] What to verify based on what was shown
- [ ] Edge cases visible in the recording

Rules:
- Be concrete — no generic placeholders
- Quote exact UI text or error messages when relevant
- If the recording shows a bug, frame the PR as fixing it; if a feature, frame it as adding it"""

SYNTHESIS_PROMPT_DESCRIPTION = """You are analyzing a screen recording or screenshot to produce a clear descriptive document.

Raw observations:

{frame_analyses}

Context: {context}
Codebase: {codebase_context}

Output EXACTLY this format:

## Overview
1–2 sentences: what this recording shows and why it matters.

## What Was Shown
Narrative description of the content in order. Reference exact text and UI state seen.

## Key Details
- Exact text visible (quote verbatim)
- Errors, URLs, status codes, code snippets
- UI elements and their state

## Context & Significance
How this relates to the provided context. What is notable or important.

## Recommendations
Concrete takeaways or action items from this recording.

Rules:
- Write for a technical audience
- Quote exact text from the screen
- Be specific — avoid vague generalizations"""


def analyze_frames(
    frames: list[dict],
    backend_name: str | None = None,
    verbose: bool = False,
    parallel: int = 1,
    **backend_kwargs,
) -> list[dict]:
    """Analyze individual frames using the configured backend.

    Args:
        frames: List of frame dicts with frame_path, timestamp, frame_index.
        parallel: Number of concurrent workers. 1 = sequential (default).

    Returns list of dicts with frame_index, timestamp, analysis (text).
    """
    backend = get_backend(backend_name, **backend_kwargs)

    if not frames:
        return []

    def _analyze_one(frame: dict) -> dict:
        if verbose:
            from .extract import fmt_timestamp
            print(
                f"  Analyzing frame {frame['frame_index']} "
                f"@ {fmt_timestamp(frame['timestamp'])}...",
                file=sys.stderr,
            )

        prompt = FRAME_ANALYSIS_PROMPT.format(
            frame_index=frame["frame_index"],
            timestamp=f"{frame['timestamp']:.1f}s",
        )

        text = backend.analyze_image(frame["frame_path"], prompt, verbose=verbose)

        return {
            "frame_index": frame["frame_index"],
            "timestamp": frame["timestamp"],
            "analysis": text,
        }

    if parallel > 1 and len(frames) > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        workers = min(parallel, len(frames))
        results = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_analyze_one, f): f for f in frames}
            for future in as_completed(futures):
                results.append(future.result())
        # Sort by frame_index to maintain order
        results.sort(key=lambda r: r["frame_index"])
        return results

    return [_analyze_one(frame) for frame in frames]


def analyze_video_direct(
    video_path: str,
    duration: float,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> str:
    """Send the full video to the backend for analysis.

    Only works with backends that support direct video input (e.g. Gemini).
    Returns the analysis text.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    if verbose:
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(
            f"  Sending full video ({file_size_mb:.1f}MB, {duration:.0f}s)...",
            file=sys.stderr,
        )

    prompt = VIDEO_ANALYSIS_PROMPT.format(duration=f"{duration:.0f}")
    return backend.analyze_video(video_path, prompt, verbose=verbose)


def analyze_audio(
    audio_path: str,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> str:
    """Transcribe audio using the configured backend."""
    backend = get_backend(backend_name, **backend_kwargs)

    if verbose:
        print("  Transcribing audio...", file=sys.stderr)

    return backend.analyze_audio(audio_path, AUDIO_PROMPT, verbose=verbose)


_OUTPUT_MODE_PROMPTS = {
    "quick": SYNTHESIS_PROMPT_QUICK,
    "minimal": SYNTHESIS_PROMPT_MINIMAL,
    "pr": SYNTHESIS_PROMPT_PR,
    "description": SYNTHESIS_PROMPT_DESCRIPTION,
}


def synthesize_report(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    context: str | None = None,
    codebase_context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    output_mode: str = "default",
    **backend_kwargs,
) -> str:
    """Combine all analysis signals into structured notes.

    Returns markdown report.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    if frame_analyses:
        from .extract import fmt_timestamp
        frame_text = "\n\n".join(
            f"### Frame {fa['frame_index']} @ {fmt_timestamp(fa['timestamp'])}\n{fa['analysis']}"
            for fa in frame_analyses
        )
    elif video_analysis:
        frame_text = f"### Full video analysis\n{video_analysis}"
    else:
        frame_text = "(no visual analysis available)"

    template = _OUTPUT_MODE_PROMPTS.get(output_mode, SYNTHESIS_PROMPT)
    prompt = template.format(
        frame_analyses=frame_text,
        context=context or "(no additional context provided)",
        transcript=transcript or "(no audio / silent recording)",
        codebase_context=codebase_context or "(no codebase context available — all file paths and function names below are hypotheses, not confirmed facts)",
    )

    if verbose:
        print("  Synthesizing report...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)
