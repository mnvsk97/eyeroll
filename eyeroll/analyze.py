"""Analyze video frames and audio to produce structured notes."""

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

Synthesize this into structured, actionable notes. Output EXACTLY this format:

## Video Analysis

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

### Bug Description
Describe the bug or issue shown in the recording in plain language.
- What is the expected behavior vs. the actual behavior?
- What triggers the issue?
If this isn't a bug, describe the feature being demonstrated or requested instead.

### Fix Directions
You are helping a coding agent working INSIDE the user's codebase. Categorize every claim:

**Visible in recording** (directly observed — error messages, URLs, UI state, code on screen):
- List specific observations with exact quoted text

**Informed by codebase context** (referencing files/functions from the project context above):
- Only reference files and functions that appear in the "Codebase context" section
- Explain which file and why it's relevant

**Hypothesis (not confirmed)** (educated guesses about root cause):
- Clearly label these as guesses
- Explain the reasoning behind each guess

**Suggested search patterns**: grep/ripgrep patterns the coding agent should run to locate relevant code.
**How to fix**: concrete steps. Reference actual project files when codebase context is available.
**What to verify**: how to confirm the fix works.

### Suggested Next Steps
Based on what was shown, what actions could a developer take?
(e.g., fix a bug, build a feature, investigate further, create a skill, etc.)

### Clarifying Questions
List any questions that would help understand what was shown better.
Only include if something is genuinely unclear — don't pad with generic questions.

---

Rules:
- Only include information you can actually see or hear in the recording
- Quote text from the screen EXACTLY — don't paraphrase
- If you're unsure about something, say "unclear" rather than guessing
- If the context text adds useful information, incorporate it
- Don't assume this is a bug — it could be a demo, tutorial, feature request, or anything else
- Keep it concise and actionable
- In Fix Directions, NEVER state a file path as fact unless it appears in the codebase context section. If no codebase context is available, ALL file paths are hypotheses — say so explicitly. Use "search for [pattern]" instead of inventing paths.
- The "Fix Directions" section is CRITICAL — this report will be read by a coding agent, not a human. Be precise and codebase-oriented."""


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
        import os
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


def synthesize_report(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    context: str | None = None,
    codebase_context: str | None = None,
    backend_name: str | None = None,
    verbose: bool = False,
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

    prompt = SYNTHESIS_PROMPT.format(
        frame_analyses=frame_text,
        context=context or "(no additional context provided)",
        transcript=transcript or "(no audio / silent recording)",
        codebase_context=codebase_context or "(no codebase context available — all file paths and function names below are hypotheses, not confirmed facts)",
    )

    if verbose:
        print("  Synthesizing report...", file=sys.stderr)

    return backend.generate(prompt, verbose=verbose)
