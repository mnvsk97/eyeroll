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
    # Clear EYEROLL_BACKEND so the default (gemini) is used and parallel=3
    env = {k: v for k, v in os.environ.items() if k != "EYEROLL_BACKEND"}
    with patch("eyeroll.watch.watch", return_value=report) as mock_watch, \
         patch.dict(os.environ, env, clear=True):
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
        base_url=None,
        verbose=False,
        no_cache=False,
        no_context=False,
        parallel=3,  # default for API backends (gemini)
        min_audio_confidence=0.4,
        scene_threshold=30.0,
        no_cost=False,
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

def test_init_gemini(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "ok"
    mock_client.models.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    with patch("eyeroll.cli._ENV_PATH", env_path), \
         patch.dict("sys.modules", {"google": MagicMock(), "google.genai": mock_genai}), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_APPLICATION_CREDENTIALS": ""}, clear=False):
        # Choose gemini, confirm overwrite (if creds exist), choose API key, enter key
        result = runner.invoke(cli, ["init"], input="1\ny\n1\ntest-api-key-123\n")

    assert result.exit_code == 0
    assert "Setup complete" in result.output
    assert os.path.isfile(env_path)
    with open(env_path) as f:
        content = f.read()
        assert "GEMINI_API_KEY=test-api-key-123" in content
        assert "EYEROLL_BACKEND=gemini" in content


def test_init_openai(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    mock_openai_mod = MagicMock()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_mod.OpenAI.return_value = mock_client

    with patch("eyeroll.cli._ENV_PATH", env_path), \
         patch.dict("sys.modules", {"openai": mock_openai_mod}):
        result = runner.invoke(cli, ["init"], input="2\nsk-test-key-456\n")

    assert result.exit_code == 0
    assert "Setup complete" in result.output
    with open(env_path) as f:
        content = f.read()
        assert "OPENAI_API_KEY=sk-test-key-456" in content
        assert "EYEROLL_BACKEND=openai" in content


def test_init_ollama(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    with patch("eyeroll.cli._ENV_PATH", env_path):
        result = runner.invoke(cli, ["init"], input="3\n")

    assert result.exit_code == 0
    assert "Setup complete" in result.output
    with open(env_path) as f:
        assert "EYEROLL_BACKEND=ollama" in content if (content := f.read()) else False


def test_init_validation_failure(runner, tmp_path):
    env_path = str(tmp_path / ".eyeroll" / ".env")

    mock_genai = MagicMock()
    mock_genai.Client.side_effect = Exception("Invalid API key")
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    with patch("eyeroll.cli._ENV_PATH", env_path), \
         patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
        # Choose 1 (gemini), enter bad key
        result = runner.invoke(cli, ["init"], input="1\nbad-key\n")

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


def test_watch_no_context_flag(runner):
    """--no-context flag is passed through to watch()."""
    with patch("eyeroll.watch.watch", return_value="report") as mock_watch:
        result = runner.invoke(cli, ["watch", "/fake/video.mp4", "--no-context"])

    assert result.exit_code == 0
    assert mock_watch.call_args[1]["no_context"] is True


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


# ---------------------------------------------------------------------------
# eyeroll history
# ---------------------------------------------------------------------------

def test_history_empty(runner):
    """History with no cache shows empty message."""
    with patch("eyeroll.history.list_history", return_value=[]):
        result = runner.invoke(cli, ["history"])

    assert result.exit_code == 0
    assert "No cached analyses found" in result.output


def test_history_lists_entries(runner):
    """History lists entries in human-readable format."""
    entries = [
        {"key": "bbb222", "source": "https://loom.com/share/xyz",
         "timestamp": "2024-01-15T14:30:00+00:00"},
        {"key": "aaa111", "source": "video.mp4",
         "timestamp": "2024-01-15T13:00:00+00:00", "media_type": "video"},
    ]
    with patch("eyeroll.history.list_history", return_value=entries):
        result = runner.invoke(cli, ["history"])

    assert result.exit_code == 0
    assert "bbb222" in result.output
    assert "aaa111" in result.output
    assert "loom.com" in result.output
    assert "(video)" in result.output


def test_history_with_limit(runner):
    """--limit is passed through to list_history."""
    with patch("eyeroll.history.list_history", return_value=[]) as mock_list:
        result = runner.invoke(cli, ["history", "--limit", "5"])

    assert result.exit_code == 0
    mock_list.assert_called_once_with(limit=5)


def test_history_json_output(runner):
    """--json outputs valid JSON."""
    entries = [
        {"key": "aaa111", "source": "video.mp4",
         "timestamp": "2024-01-15T13:00:00+00:00"},
    ]
    with patch("eyeroll.history.list_history", return_value=entries):
        result = runner.invoke(cli, ["history", "--json"])

    assert result.exit_code == 0
    import json
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    assert parsed[0]["key"] == "aaa111"


def test_history_clear_with_confirm(runner):
    """History clear asks for confirmation and clears."""
    entries = [{"key": "aaa111", "source": "v.mp4", "timestamp": "2024-01-15T13:00:00+00:00"}]
    with patch("eyeroll.history.list_history", return_value=entries), \
         patch("eyeroll.history.clear_history") as mock_clear:
        result = runner.invoke(cli, ["history", "clear"], input="y\n")

    assert result.exit_code == 0
    assert "Cleared 1" in result.output
    mock_clear.assert_called_once()


def test_history_clear_aborted(runner):
    """History clear aborted when user says no."""
    entries = [{"key": "aaa111", "source": "v.mp4", "timestamp": "2024-01-15T13:00:00+00:00"}]
    with patch("eyeroll.history.list_history", return_value=entries), \
         patch("eyeroll.history.clear_history") as mock_clear:
        result = runner.invoke(cli, ["history", "clear"], input="n\n")

    assert result.exit_code == 0
    assert "Aborted" in result.output
    mock_clear.assert_not_called()


def test_history_clear_yes_flag(runner):
    """--yes skips confirmation."""
    entries = [{"key": "aaa111", "source": "v.mp4", "timestamp": "2024-01-15T13:00:00+00:00"}]
    with patch("eyeroll.history.list_history", return_value=entries), \
         patch("eyeroll.history.clear_history") as mock_clear:
        result = runner.invoke(cli, ["history", "clear", "--yes"])

    assert result.exit_code == 0
    mock_clear.assert_called_once()


def test_history_clear_already_empty(runner):
    """Clear on empty cache shows message."""
    with patch("eyeroll.history.list_history", return_value=[]):
        result = runner.invoke(cli, ["history", "clear"])

    assert result.exit_code == 0
    assert "already empty" in result.output
