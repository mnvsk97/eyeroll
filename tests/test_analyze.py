"""Tests for the analyze module."""

from unittest.mock import MagicMock, patch, call

import pytest

from eyeroll.analyze import (
    analyze_audio,
    analyze_frames,
    analyze_video_direct,
    synthesize_report,
    FRAME_ANALYSIS_PROMPT,
    VIDEO_ANALYSIS_PROMPT,
    AUDIO_PROMPT,
    SYNTHESIS_PROMPT,
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
    """Verify the prompt instructs the model to categorize claims."""
    assert "Visible in recording" in SYNTHESIS_PROMPT
    assert "Informed by codebase context" in SYNTHESIS_PROMPT
    assert "Hypothesis" in SYNTHESIS_PROMPT


def test_synthesis_prompt_has_bug_description():
    """Verify the prompt includes a Bug Description section."""
    assert "Bug Description" in SYNTHESIS_PROMPT


def test_synthesis_prompt_forbids_invented_paths():
    """Verify the prompt tells the model not to invent file paths."""
    assert "NEVER state a file path as fact unless it appears in the codebase context" in SYNTHESIS_PROMPT
