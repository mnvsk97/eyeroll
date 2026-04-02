"""Tests for the CLI module."""

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from eyeroll.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# eyeroll watch — basic invocation
# ---------------------------------------------------------------------------

def test_watch_local_file(runner, tmp_path):
    report = "# eyeroll: test\n\n## Report content"

    with patch("eyeroll.cli.watch") as mock_cmd:
        # The lazy import inside the command
        with patch("eyeroll.watch.watch", return_value=report) as mock_watch:
            # We need to patch at the point of import inside the command
            with patch("eyeroll.cli.watch") as _:
                pass

    # Simpler approach: patch the function that the CLI calls
    with patch("eyeroll.watch.watch", return_value=report):
        result = runner.invoke(cli, ["watch", str(tmp_path / "video.mp4")])
        # This will fail with FileNotFoundError since run_watch is imported lazily
        # Let's patch at the right level

    # The CLI does: from .watch import watch as run_watch
    # So we patch eyeroll.watch.watch
    with patch("eyeroll.watch.watch", return_value=report) as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4"])

    assert result.exit_code == 0
    assert "# eyeroll: test" in result.output
    mock_watch.assert_called_once_with(
        source="/fake/video.mp4",
        context=None,
        codebase_context=None,
        max_frames=20,
        backend_name=None,
        model=None,
        verbose=False,
        no_cache=False,
    )


def test_watch_with_context(runner):
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--context", "broken login"])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["context"] == "broken login"


def test_watch_with_backend_and_model(runner):
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, [
            "watch", "/fake/video.mp4",
            "--backend", "ollama",
            "--model", "qwen3-vl:8b",
        ])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["backend_name"] == "ollama"
    assert mock_watch.call_args[1]["model"] == "qwen3-vl:8b"


def test_watch_model_without_backend_auto_selects_ollama(runner):
    """Passing --model without --backend auto-selects ollama for non-gemini models."""
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--model", "qwen3-vl:2b"])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["backend_name"] == "ollama"
    assert mock_watch.call_args[1]["model"] == "qwen3-vl:2b"


def test_watch_model_gemini_stays_none_backend(runner):
    """Passing --model gemini-2.0-flash without --backend keeps backend=None."""
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--model", "gemini-2.0-flash"])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["backend_name"] is None


# ---------------------------------------------------------------------------
# eyeroll watch --output
# ---------------------------------------------------------------------------

def test_watch_with_output_flag(runner, tmp_path):
    output_file = str(tmp_path / "report.md")

    with patch("eyeroll.watch.watch", return_value="# Report content"):
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--output", output_file])

    assert result.exit_code == 0
    assert os.path.isfile(output_file)
    with open(output_file) as f:
        assert f.read() == "# Report content"


# ---------------------------------------------------------------------------
# eyeroll watch — error handling
# ---------------------------------------------------------------------------

def test_watch_file_not_found(runner):
    with patch("eyeroll.watch.watch", side_effect=FileNotFoundError("File not found: /bad/path.mp4")):
        result = runner.invoke(cli, ["watch", "/bad/path.mp4"])

    assert result.exit_code == 1
    assert "File not found" in result.output or "Error" in (result.output + getattr(result, 'stderr', ''))


def test_watch_runtime_error(runner):
    with patch("eyeroll.watch.watch", side_effect=RuntimeError("yt-dlp failed")):
        result = runner.invoke(cli, ["watch", "https://example.com/video"])

    assert result.exit_code == 1


def test_watch_generic_error(runner):
    with patch("eyeroll.watch.watch", side_effect=Exception("Something unexpected")):
        result = runner.invoke(cli, ["watch", "/fake/video.mp4"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# eyeroll watch --verbose
# ---------------------------------------------------------------------------

def test_watch_verbose_flag(runner):
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--verbose"])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["verbose"] is True


# ---------------------------------------------------------------------------
# eyeroll init
# ---------------------------------------------------------------------------

def test_init_command(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "ok"
    mock_client.models.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    with patch("eyeroll.cli._ENV_PATH", env_path), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}):
        result = runner.invoke(cli, ["init"], input="test-api-key-123\n")

    assert result.exit_code == 0
    assert "Setup complete" in result.output
    assert os.path.isfile(env_path)
    with open(env_path) as f:
        assert "GEMINI_API_KEY=test-api-key-123" in f.read()


def test_init_validation_failure(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    mock_genai = MagicMock()
    mock_genai.Client.side_effect = Exception("Invalid API key")
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    with patch("eyeroll.cli._ENV_PATH", env_path), \
         patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
        result = runner.invoke(cli, ["init"], input="bad-key\n")

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# eyeroll watch --codebase-context
# ---------------------------------------------------------------------------

def test_watch_with_codebase_context_inline(runner):
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, [
            "watch", "/fake/video.mp4",
            "--codebase-context", "Python app, key file: src/api.py",
        ])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["codebase_context"] == "Python app, key file: src/api.py"


def test_watch_with_codebase_context_file(runner, tmp_path):
    ctx_file = tmp_path / "context.md"
    ctx_file.write_text("## Project: myapp\n**Stack:** Python")

    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, [
            "watch", "/fake/video.mp4",
            "--codebase-context", str(ctx_file),
        ])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["codebase_context"] == "## Project: myapp\n**Stack:** Python"
