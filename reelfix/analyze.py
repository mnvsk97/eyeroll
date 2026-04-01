"""Analyze video frames and audio using Gemini to produce a structured bug report."""

import base64
import os
import sys

from dotenv import load_dotenv

load_dotenv()


class AnalysisError(RuntimeError):
    """Raised when video analysis fails."""


def _get_gemini_client():
    from google import genai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AnalysisError(
            "GEMINI_API_KEY is not set.\n\n"
            "Get a free key at: https://aistudio.google.com/apikey\n"
            "Then: export GEMINI_API_KEY=your-key"
        )
    return genai.Client(api_key=api_key)


def _encode_image(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, mime_type


FRAME_ANALYSIS_PROMPT = """You are analyzing a screen recording of a software bug.
This is frame {frame_index} at timestamp {timestamp}.

Look at this screenshot carefully and extract:

1. **PAGE/URL**: What page, URL, or route is visible? (check address bar, breadcrumbs, page title)
2. **UI STATE**: What UI elements are visible? (forms, buttons, modals, tables, navigation)
3. **ERRORS**: Any error messages, red text, warning banners, toast notifications, error modals, console errors?
4. **TEXT ON SCREEN**: All significant text visible — exact wording of error messages, labels, headings.
5. **USER ACTION**: Any indication of what the user just did or is about to do? (cursor position, active element, form state)

Be precise. Quote exact text from the screen. If you can't read something clearly, say so.
Do NOT hallucinate or guess text you can't see clearly."""

VIDEO_ANALYSIS_PROMPT = """You are analyzing a screen recording of a software bug.
The video is {duration} seconds long.

Watch the entire video carefully and describe:

1. **STEPS**: What is the user doing step by step? (navigating, clicking, typing, scrolling)
2. **PAGE/URL**: What pages or routes are visited?
3. **ERRORS**: Any error messages, failed requests, broken UI, unexpected behavior?
4. **TEXT ON SCREEN**: Exact error messages, status codes, console output visible.
5. **THE BUG**: What appears to go wrong? At what point does the unexpected behavior occur?
6. **EXPECTED vs ACTUAL**: What likely should have happened vs what did happen?

Be precise. Quote exact text. Don't guess what you can't see clearly."""

SYNTHESIS_PROMPT = """You are a senior developer analyzing a bug report generated from a screen recording.

Here are the raw observations from the video:

## Frame-by-frame analysis:
{frame_analyses}

## Additional context from the reporter:
{context}

## Audio transcript (if available):
{transcript}

---

Synthesize this into a structured, actionable bug report. Output EXACTLY this format:

## Bug Report

### Summary
One sentence describing the bug.

### Steps to Reproduce
1. Step one
2. Step two
3. ...

### Error Signals
- Exact error messages observed (quote them verbatim)
- URLs/routes where the bug occurs
- HTTP status codes if visible
- Console errors if visible

### Expected vs Actual Behavior
- **Expected:** What should happen
- **Actual:** What actually happens

### Environment Clues
- Browser/OS if visible
- Any version numbers, deployment info visible on screen

### Confidence: [high/medium/low]
State your confidence and explain what's clear vs ambiguous.

### Clarifying Questions
List any questions you'd ask the reporter to better understand the bug.
Only include if something is genuinely unclear — don't pad with generic questions.

---

Rules:
- Only include information you can actually see or hear in the recording
- Quote error messages EXACTLY — don't paraphrase
- If you're unsure about something, say "unclear" rather than guessing
- If the context text from the reporter adds useful information, incorporate it
- Keep it concise and actionable"""


def analyze_frames(
    frames: list[dict],
    verbose: bool = False,
) -> list[dict]:
    """Analyze individual frames using Gemini vision.

    Args:
        frames: list of dicts with frame_path, timestamp, frame_index.
        verbose: print progress to stderr.

    Returns:
        list of dicts with frame_index, timestamp, analysis (text).
    """
    from google.genai import types

    client = _get_gemini_client()
    results = []

    for frame in frames:
        if verbose:
            from .extract import fmt_timestamp
            print(
                f"  Analyzing frame {frame['frame_index']} "
                f"@ {fmt_timestamp(frame['timestamp'])}...",
                file=sys.stderr,
            )

        b64_data, mime_type = _encode_image(frame["frame_path"])

        prompt = FRAME_ANALYSIS_PROMPT.format(
            frame_index=frame["frame_index"],
            timestamp=f"{frame['timestamp']:.1f}s",
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=types.Content(
                parts=[
                    types.Part.from_bytes(
                        data=base64.standard_b64decode(b64_data),
                        mime_type=mime_type,
                    ),
                    types.Part(text=prompt),
                ],
            ),
        )

        results.append({
            "frame_index": frame["frame_index"],
            "timestamp": frame["timestamp"],
            "analysis": response.text,
        })

    return results


def analyze_video_direct(
    video_path: str,
    duration: float,
    verbose: bool = False,
) -> str:
    """Send the full video to Gemini for analysis (if small enough).

    Gemini Flash supports video input directly — more accurate than
    frame-by-frame for short videos.

    Returns the analysis text.
    """
    from google.genai import types

    client = _get_gemini_client()
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

    if verbose:
        print(
            f"  Sending full video to Gemini ({file_size_mb:.1f}MB, {duration:.0f}s)...",
            file=sys.stderr,
        )

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    prompt = VIDEO_ANALYSIS_PROMPT.format(duration=f"{duration:.0f}")

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=types.Content(
            parts=[
                types.Part.from_bytes(
                    data=video_bytes,
                    mime_type="video/mp4",
                ),
                types.Part(text=prompt),
            ],
        ),
    )

    return response.text


def analyze_audio(audio_path: str, verbose: bool = False) -> str:
    """Transcribe audio using Gemini."""
    from google.genai import types

    client = _get_gemini_client()

    if verbose:
        print("  Transcribing audio...", file=sys.stderr)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=types.Content(
            parts=[
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/mp3",
                ),
                types.Part(
                    text=(
                        "Transcribe this audio from a bug report video. "
                        "Include everything the speaker says. "
                        "Note any references to specific features, pages, errors, or timeframes. "
                        "If the audio is silent or contains no speech, respond with: [no speech detected]"
                    ),
                ),
            ],
        ),
    )

    return response.text


def synthesize_bug_report(
    frame_analyses: list[dict] | None = None,
    video_analysis: str | None = None,
    transcript: str | None = None,
    context: str | None = None,
    verbose: bool = False,
) -> str:
    """Combine all analysis signals into a structured bug report.

    Returns markdown bug report.
    """
    from google.genai import types

    client = _get_gemini_client()

    # Build the frame analysis section
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
    )

    if verbose:
        print("  Synthesizing bug report...", file=sys.stderr)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return response.text
