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

# ---------------------------------------------------------------------------
# Temporal analysis prompts — past / present / future
# ---------------------------------------------------------------------------

PAST_PROMPT = """You are a senior developer examining a screen recording.

Observations from the recording:
{observations}

Context from the person who shared this:
{context}

Analyze the PAST — the historical context, background, and conditions that led to what is shown.

Think like a developer investigating: What was the state of things before this recording? What led to this situation? What was the user or developer trying to accomplish? What prior actions, changes, or decisions are implied by what we see?

Draw on both the visual observations and the context text. Be concise and factual. Say "unclear" rather than guessing."""

PRESENT_PROMPT = """You are a senior developer examining a screen recording.

Observations from the recording:
{observations}

Audio transcript:
{transcript}

Codebase context:
{codebase_context}

Analyze the PRESENT — the current state as shown in the recording, across three dimensions:

- **Technical**: Errors, broken behavior, system output, code state, API responses, console logs
- **Product**: What features work, what is broken, what is incomplete, what the user experience looks like right now
- **Business**: What does this mean for users, stakeholders, or the product's goals?

Quote exact text from the recording. Note what is confirmed by direct evidence vs. what is inferred. Say "unclear" rather than guessing."""

FUTURE_PROMPT = """You are a senior developer examining a screen recording.

Historical context (Past):
{past}

Current state (Present):
{present}

Context from the person who shared this:
{context}

Reason about the FUTURE — what needs to happen to resolve this or achieve the goal.

Consider:
- What is the desired outcome? What does success look like?
- What needs to change, be built, or be fixed to get from present to that future?
- What are the concrete next steps a developer should take?
- If this is a bug: what is the expected behavior vs. actual behavior? What is the fix?
- If this is a feature request: what needs to be built? How should it behave?
- What can a coding agent act on right now?

Be specific. Reference actual evidence from Past and Present."""

TEMPORAL_SYNTHESIS_PROMPT = """You are a senior developer producing a final report from a screen recording analysis.

## Past — Context & History
{past}

## Present — Current State
{present}

## Future — Desired Outcome
{future}

## Context from the person who shared this:
{context}

---

First, determine what KIND of content this is:
- **Bug report**: shows broken behavior, errors, unexpected results
- **Feature demo**: demonstrates working functionality, a new feature, or a product walkthrough
- **Tutorial/how-to**: teaches a process or workflow step by step
- **Feature request**: shows desired behavior or proposes new functionality
- **Code review**: walks through code changes or PR diffs
- **General notes**: anything else

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
- **scope**: "in-context" if the video relates to the codebase described in context, "out-of-context" if unrelated or no codebase context provided
- **severity**: "critical" for crashes/data loss/security issues, "moderate" for broken features/errors, "low" for cosmetic/minor issues. For non-bugs, base on importance.
- **actionable**: "yes" if a coding agent can take concrete action (fix a bug, build a feature, create a skill), "no" if it's just informational

### Content Type: [bug report | feature demo | tutorial | feature request | code review | general notes]
State what kind of content this is.

### Summary
One or two sentences describing what this recording shows.

### Temporal Narrative
A developer's coherent story: what led to this (past) → what is happening now (present) → what needs to happen (future).

### Key Evidence
- Exact text from the screen (error messages, URLs, labels, code — quoted verbatim)
- UI elements and their state
- HTTP status codes, console output, network requests if visible
- Environment, version, or configuration info

### Audio/Narration Summary
Key points from what was said. Or "(silent recording)" if no audio.

### Analysis
<!-- Adapt based on content type -->

**If bug report:**

### Reproduction Steps
Minimal steps to reproduce:
1. Step one
2. Step two

- Expected behavior vs. actual behavior
- Evidence:
  - **Visible in recording**: directly observed (quote exact text)
  - **Informed by codebase context**: only reference files from the codebase context section
  - **Hypothesis (not confirmed)**: educated guesses, clearly labeled
- Suggested search patterns for the coding agent
- How to fix (concrete steps, reference actual project files when available)
- How to verify the fix

**If feature demo:**
- What feature or workflow is being demonstrated
- Key capabilities shown
- How it relates to the codebase

**If tutorial/how-to:**
- What process is being taught
- Tools and commands used
- Key steps to reproduce
- Could this be automated into a skill or script?

**If feature request:**
- What is being requested
- Desired behavior
- How it differs from current behavior

**If code review:**
- Files/functions reviewed
- Key changes discussed
- Concerns or approvals noted

**If general notes:**
- Key points and takeaways
- Action items

### Suggested Next Steps
Concrete actions based on content type.

### Clarifying Questions
Only include if something is genuinely unclear — don't pad with generic questions.

---

Rules:
- Only include information from the temporal analyses and context above
- Quote text EXACTLY — don't paraphrase
- If uncertain, say so rather than guessing
- Do NOT assume this is a bug — determine type from evidence first
- NEVER state a file path as fact unless it appears in the codebase context. All other paths are hypotheses — say so explicitly.
- This report will be read by a coding agent. Be precise and actionable."""

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


def _format_observations(
    frame_analyses: list[dict] | None,
    video_analysis: str | None,
) -> str:
    """Format raw frame/video observations into a flat text block."""
    if frame_analyses:
        from .extract import fmt_timestamp
        return "\n\n".join(
            f"Frame {fa['frame_index']} @ {fmt_timestamp(fa['timestamp'])}: {fa['analysis']}"
            for fa in frame_analyses
        )
    if video_analysis:
        return video_analysis
    return "(no visual observations available)"


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


def analyze_past(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> str:
    """Analyze the historical context — what led to this recording.

    Returns a text analysis of the past: background, preconditions, what the
    user or developer was trying to accomplish before this moment.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    observations = _format_observations(frame_analyses, video_analysis)
    prompt = PAST_PROMPT.format(
        observations=observations,
        context=context or "(no additional context provided)",
    )

    if verbose:
        print("  Analyzing past (historical context)...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)


def analyze_present(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    codebase_context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> str:
    """Analyze the current state shown in the recording.

    Returns a text analysis of the present: technical state, product state,
    and business impact — what is happening right now.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    observations = _format_observations(frame_analyses, video_analysis)
    prompt = PRESENT_PROMPT.format(
        observations=observations,
        transcript=transcript or "(no audio / silent recording)",
        codebase_context=codebase_context or "(no codebase context available — all file paths and function names are hypotheses, not confirmed facts)",
    )

    if verbose:
        print("  Analyzing present (current state)...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)


def analyze_future(
    past: str,
    present: str,
    context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> str:
    """Reason about the desired future — what needs to happen next.

    Takes past and present analyses and reasons toward the desired outcome,
    success criteria, and concrete developer next steps.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    prompt = FUTURE_PROMPT.format(
        past=past,
        present=present,
        context=context or "(no additional context provided)",
    )

    if verbose:
        print("  Analyzing future (desired outcome)...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)


def analyze_temporal(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    context: str | None = None,
    codebase_context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    **backend_kwargs,
) -> dict:
    """Run the full past/present/future temporal analysis.

    Returns a dict with keys: past, present, future — each a text analysis
    representing one temporal lens on the recording.
    """
    past = analyze_past(
        frame_analyses=frame_analyses,
        video_analysis=video_analysis,
        context=context,
        backend_name=backend_name,
        verbose=verbose,
        **backend_kwargs,
    )
    present = analyze_present(
        frame_analyses=frame_analyses,
        video_analysis=video_analysis,
        transcript=transcript,
        codebase_context=codebase_context,
        backend_name=backend_name,
        verbose=verbose,
        **backend_kwargs,
    )
    future = analyze_future(
        past=past,
        present=present,
        context=context,
        backend_name=backend_name,
        verbose=verbose,
        **backend_kwargs,
    )
    return {"past": past, "present": present, "future": future}


def synthesize_report(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    context: str | None = None,
    codebase_context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
    past: str | None = None,
    present: str | None = None,
    future: str | None = None,
    **backend_kwargs,
) -> str:
    """Combine all analysis signals into structured notes.

    When past/present/future temporal analyses are provided, uses the temporal
    synthesis path. Otherwise falls back to raw frame analysis (legacy path).

    Returns markdown report.
    """
    backend = get_backend(backend_name, **backend_kwargs)

    if past is not None and present is not None and future is not None:
        prompt = TEMPORAL_SYNTHESIS_PROMPT.format(
            past=past,
            present=present,
            future=future,
            context=context or "(no additional context provided)",
        )
    else:
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

        prompt = SYNTHESIS_PROMPT.format(
            frame_analyses=frame_text,
            context=context or "(no additional context provided)",
            transcript=transcript or "(no audio / silent recording)",
            codebase_context=codebase_context or "(no codebase context available — all file paths and function names below are hypotheses, not confirmed facts)",
        )

    if verbose:
        print("  Synthesizing report...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)
