"""Tests for the analyze module."""

from unittest.mock import MagicMock, patch, call

import pytest

from eyeroll.analyze import (
    analyze_audio,
    analyze_frames,
    analyze_past,
    analyze_present,
    analyze_future,
    analyze_temporal,
    analyze_video_direct,
    synthesize_report,
    FRAME_ANALYSIS_PROMPT,
    VIDEO_ANALYSIS_PROMPT,
    AUDIO_PROMPT,
    SYNTHESIS_PROMPT,
    TEMPORAL_SYNTHESIS_PROMPT,
    PAST_PROMPT,
    PRESENT_PROMPT,
    FUTURE_PROMPT,
)


# ---------------------------------------------------------------------------
# analyze_frames
# ---------------------------------------------------------------------------

def test_analyze_frames_calls_backend_per_frame():
    mock_backend = MagicMock()
    mock_backend.analyze_image.side_effect = ["analysis_0", "analysis_1", "analysis_2"]

    frames = [
        {"frame_path": "/tmp/f0.jpg", "timestamp": 0.0, "frame_index": 0},
        {"frame_path": "/tmp/f1.jpg", "timestamp": 5.0, "frame_index": 1},
        {"frame_path": "/tmp/f2.jpg", "timestamp": 10.0, "frame_index": 2},
    ]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        results = analyze_frames(frames)

    assert len(results) == 3
    assert results[0]["analysis"] == "analysis_0"
    assert results[1]["frame_index"] == 1
    assert results[2]["timestamp"] == 10.0
    assert mock_backend.analyze_image.call_count == 3
    # Verify the image paths passed
    assert mock_backend.analyze_image.call_args_list[0][0][0] == "/tmp/f0.jpg"
    assert mock_backend.analyze_image.call_args_list[2][0][0] == "/tmp/f2.jpg"


def test_analyze_frames_empty():
    mock_backend = MagicMock()

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        results = analyze_frames([])

    assert results == []
    mock_backend.analyze_image.assert_not_called()


def test_analyze_frames_prompt_formatting():
    """Verify the prompt includes frame_index and timestamp."""
    mock_backend = MagicMock()
    mock_backend.analyze_image.return_value = "ok"

    frames = [{"frame_path": "/tmp/f.jpg", "timestamp": 7.3, "frame_index": 5}]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_frames(frames)

    prompt_arg = mock_backend.analyze_image.call_args[0][1]
    assert "frame 5" in prompt_arg.lower() or "5" in prompt_arg
    assert "7.3s" in prompt_arg


def test_analyze_frames_parallel():
    """Parallel analysis returns results in correct order."""
    mock_backend = MagicMock()
    mock_backend.analyze_image.side_effect = ["a0", "a1", "a2", "a3"]

    frames = [
        {"frame_path": f"/tmp/f{i}.jpg", "timestamp": float(i), "frame_index": i}
        for i in range(4)
    ]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        results = analyze_frames(frames, parallel=3)

    assert len(results) == 4
    # Results should be sorted by frame_index regardless of completion order
    assert [r["frame_index"] for r in results] == [0, 1, 2, 3]
    assert mock_backend.analyze_image.call_count == 4


# ---------------------------------------------------------------------------
# analyze_video_direct
# ---------------------------------------------------------------------------

def test_analyze_video_direct():
    mock_backend = MagicMock()
    mock_backend.analyze_video.return_value = "Video analysis result"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_video_direct("/path/to/video.mp4", duration=45.0)

    assert result == "Video analysis result"
    mock_backend.analyze_video.assert_called_once()
    # Check prompt includes duration
    prompt_arg = mock_backend.analyze_video.call_args[0][1]
    assert "45" in prompt_arg


# ---------------------------------------------------------------------------
# analyze_audio
# ---------------------------------------------------------------------------

def test_analyze_audio():
    mock_backend = MagicMock()
    mock_backend.analyze_audio.return_value = "Transcript of audio"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_audio("/path/to/audio.mp3")

    assert result == "Transcript of audio"
    mock_backend.analyze_audio.assert_called_once()
    assert mock_backend.analyze_audio.call_args[0][0] == "/path/to/audio.mp3"
    assert mock_backend.analyze_audio.call_args[0][1] == AUDIO_PROMPT


# ---------------------------------------------------------------------------
# synthesize_report
# ---------------------------------------------------------------------------

def test_synthesize_report_with_frame_analyses():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "## Synthesized Report"

    frame_analyses = [
        {"frame_index": 0, "timestamp": 0.0, "analysis": "Frame 0 analysis"},
        {"frame_index": 1, "timestamp": 5.0, "analysis": "Frame 1 analysis"},
    ]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = synthesize_report(frame_analyses=frame_analyses, context="bug after PR #42")

    assert result == "## Synthesized Report"
    mock_backend.generate.assert_called_once()
    prompt = mock_backend.generate.call_args[0][0]
    assert "Frame 0 analysis" in prompt
    assert "Frame 1 analysis" in prompt
    assert "bug after PR #42" in prompt


def test_synthesize_report_with_video_analysis():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report from video"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = synthesize_report(video_analysis="Full video observation")

    prompt = mock_backend.generate.call_args[0][0]
    assert "Full video analysis" in prompt or "Full video observation" in prompt


def test_synthesize_report_no_analyses():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Empty report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = synthesize_report()

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no visual analysis available)" in prompt


def test_synthesize_report_no_context():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report(frame_analyses=[
            {"frame_index": 0, "timestamp": 0.0, "analysis": "test"}
        ])

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no additional context provided)" in prompt


def test_synthesize_report_no_transcript():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report()

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no audio / silent recording)" in prompt


def test_synthesize_report_with_transcript():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report(transcript="The user says: click the button")

    prompt = mock_backend.generate.call_args[0][0]
    assert "The user says: click the button" in prompt


# ---------------------------------------------------------------------------
# synthesize_report — codebase context
# ---------------------------------------------------------------------------

def test_synthesize_report_with_codebase_context():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report(
            frame_analyses=[{"frame_index": 0, "timestamp": 0.0, "analysis": "test"}],
            codebase_context="## Project: myapp\n**Stack:** Python\n- src/api.py",
        )

    prompt = mock_backend.generate.call_args[0][0]
    assert "## Project: myapp" in prompt
    assert "src/api.py" in prompt


def test_synthesize_report_no_codebase_context():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report()

    prompt = mock_backend.generate.call_args[0][0]
    assert "no codebase context available" in prompt
    assert "hypotheses" in prompt


def test_synthesis_prompt_has_confidence_tiers():
    """Verify the prompt instructs the model to categorize claims for bug reports."""
    assert "Visible in recording" in SYNTHESIS_PROMPT
    assert "Informed by codebase context" in SYNTHESIS_PROMPT
    assert "Hypothesis" in SYNTHESIS_PROMPT


def test_synthesis_prompt_detects_content_type():
    """Verify the prompt asks the model to determine content type."""
    assert "Content Type" in SYNTHESIS_PROMPT
    assert "bug report" in SYNTHESIS_PROMPT
    assert "feature demo" in SYNTHESIS_PROMPT
    assert "tutorial" in SYNTHESIS_PROMPT


def test_synthesis_prompt_forbids_invented_paths():
    """Verify the prompt tells the model not to invent file paths."""
    assert "NEVER state a file path as fact unless it appears in the codebase context" in SYNTHESIS_PROMPT


def test_synthesis_prompt_does_not_assume_bugs():
    """Verify the prompt explicitly says not to assume bugs."""
    assert "Do NOT assume this is a bug" in SYNTHESIS_PROMPT


# ---------------------------------------------------------------------------
# analyze_past
# ---------------------------------------------------------------------------

def test_analyze_past_calls_backend_generate():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Past analysis text"

    frame_analyses = [{"frame_index": 0, "timestamp": 0.0, "analysis": "login page shown"}]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_past(frame_analyses=frame_analyses, context="auth broke after deploy")

    assert result == "Past analysis text"
    mock_backend.generate.assert_called_once()
    prompt = mock_backend.generate.call_args[0][0]
    assert "login page shown" in prompt
    assert "auth broke after deploy" in prompt


def test_analyze_past_with_video_analysis():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Past from video"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_past(video_analysis="user navigates to settings page")

    prompt = mock_backend.generate.call_args[0][0]
    assert "user navigates to settings page" in prompt


def test_analyze_past_no_context_fallback():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Past"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_past()

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no additional context provided)" in prompt


# ---------------------------------------------------------------------------
# analyze_present
# ---------------------------------------------------------------------------

def test_analyze_present_calls_backend_generate():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Present analysis text"

    frame_analyses = [{"frame_index": 0, "timestamp": 0.0, "analysis": "error 500 shown"}]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_present(
            frame_analyses=frame_analyses,
            transcript="the server is crashing",
            codebase_context="## Project: myapp",
        )

    assert result == "Present analysis text"
    prompt = mock_backend.generate.call_args[0][0]
    assert "error 500 shown" in prompt
    assert "the server is crashing" in prompt
    assert "## Project: myapp" in prompt


def test_analyze_present_no_transcript_fallback():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Present"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_present()

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no audio / silent recording)" in prompt


def test_analyze_present_no_codebase_context_fallback():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Present"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_present()

    prompt = mock_backend.generate.call_args[0][0]
    assert "hypotheses" in prompt


# ---------------------------------------------------------------------------
# analyze_future
# ---------------------------------------------------------------------------

def test_analyze_future_calls_backend_generate():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Future analysis text"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_future(
            past="user tried to log in",
            present="500 error on POST /auth",
            context="broke after deploy",
        )

    assert result == "Future analysis text"
    prompt = mock_backend.generate.call_args[0][0]
    assert "user tried to log in" in prompt
    assert "500 error on POST /auth" in prompt
    assert "broke after deploy" in prompt


def test_analyze_future_no_context_fallback():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Future"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_future(past="p", present="q")

    prompt = mock_backend.generate.call_args[0][0]
    assert "(no additional context provided)" in prompt


# ---------------------------------------------------------------------------
# analyze_temporal
# ---------------------------------------------------------------------------

def test_analyze_temporal_returns_dict_with_three_phases():
    mock_backend = MagicMock()
    mock_backend.generate.side_effect = ["past text", "present text", "future text"]

    frame_analyses = [{"frame_index": 0, "timestamp": 0.0, "analysis": "some UI"}]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = analyze_temporal(
            frame_analyses=frame_analyses,
            context="test context",
            codebase_context="myapp stack",
        )

    assert result == {"past": "past text", "present": "present text", "future": "future text"}
    assert mock_backend.generate.call_count == 3


def test_analyze_temporal_passes_past_to_future():
    """analyze_future receives the output of analyze_past."""
    mock_backend = MagicMock()
    mock_backend.generate.side_effect = ["past output", "present output", "future output"]

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        analyze_temporal()

    # Third call (future) should include the past and present outputs in its prompt
    future_prompt = mock_backend.generate.call_args_list[2][0][0]
    assert "past output" in future_prompt
    assert "present output" in future_prompt


# ---------------------------------------------------------------------------
# synthesize_report — temporal path
# ---------------------------------------------------------------------------

def test_synthesize_report_temporal_path():
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "## Temporal Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        result = synthesize_report(
            past="historical context here",
            present="current state here",
            future="desired outcome here",
            context="fix the login bug",
        )

    assert result == "## Temporal Report"
    prompt = mock_backend.generate.call_args[0][0]
    assert "historical context here" in prompt
    assert "current state here" in prompt
    assert "desired outcome here" in prompt
    assert "fix the login bug" in prompt


def test_synthesize_report_temporal_uses_temporal_prompt():
    """When temporal phases are given, TEMPORAL_SYNTHESIS_PROMPT is used."""
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report(past="p", present="q", future="r")

    prompt = mock_backend.generate.call_args[0][0]
    # Temporal path has "Temporal Narrative" section
    assert "Temporal Narrative" in prompt


def test_synthesize_report_falls_back_without_temporal():
    """Without temporal phases, legacy SYNTHESIS_PROMPT is used."""
    mock_backend = MagicMock()
    mock_backend.generate.return_value = "Report"

    with patch("eyeroll.analyze.get_backend", return_value=mock_backend):
        synthesize_report(frame_analyses=[
            {"frame_index": 0, "timestamp": 0.0, "analysis": "some frame"}
        ])

    prompt = mock_backend.generate.call_args[0][0]
    assert "some frame" in prompt
    # Legacy path does not have "Temporal Narrative"
    assert "Temporal Narrative" not in prompt


# ---------------------------------------------------------------------------
# TEMPORAL_SYNTHESIS_PROMPT content checks
# ---------------------------------------------------------------------------

def test_temporal_synthesis_prompt_has_confidence_tiers():
    assert "Visible in recording" in TEMPORAL_SYNTHESIS_PROMPT
    assert "Informed by codebase context" in TEMPORAL_SYNTHESIS_PROMPT
    assert "Hypothesis" in TEMPORAL_SYNTHESIS_PROMPT


def test_temporal_synthesis_prompt_detects_content_type():
    assert "Content Type" in TEMPORAL_SYNTHESIS_PROMPT
    assert "bug report" in TEMPORAL_SYNTHESIS_PROMPT
    assert "feature demo" in TEMPORAL_SYNTHESIS_PROMPT
    assert "tutorial" in TEMPORAL_SYNTHESIS_PROMPT


def test_temporal_synthesis_prompt_forbids_invented_paths():
    assert "NEVER state a file path as fact unless it appears in the codebase context" in TEMPORAL_SYNTHESIS_PROMPT


def test_temporal_synthesis_prompt_does_not_assume_bugs():
    assert "Do NOT assume this is a bug" in TEMPORAL_SYNTHESIS_PROMPT


def test_temporal_synthesis_prompt_has_three_sections():
    assert "Past" in TEMPORAL_SYNTHESIS_PROMPT
    assert "Present" in TEMPORAL_SYNTHESIS_PROMPT
    assert "Future" in TEMPORAL_SYNTHESIS_PROMPT
    assert "Temporal Narrative" in TEMPORAL_SYNTHESIS_PROMPT


# ---------------------------------------------------------------------------
# Temporal prompt content checks
# ---------------------------------------------------------------------------

def test_past_prompt_asks_about_history():
    assert "PAST" in PAST_PROMPT
    assert "historical" in PAST_PROMPT.lower() or "history" in PAST_PROMPT.lower()


def test_present_prompt_covers_three_dimensions():
    assert "Technical" in PRESENT_PROMPT
    assert "Product" in PRESENT_PROMPT
    assert "Business" in PRESENT_PROMPT


def test_future_prompt_asks_about_desired_outcome():
    assert "FUTURE" in FUTURE_PROMPT
    assert "desired" in FUTURE_PROMPT.lower() or "outcome" in FUTURE_PROMPT.lower()
