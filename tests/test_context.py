"""Tests for the context auto-discovery module."""

import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from eyeroll.context import (
    discover_context,
    _find_git_root,
    _is_stale,
    _scan_tier1,
    _scan_tier2,
    TIER1_FILES,
)


# ---------------------------------------------------------------------------
# _find_git_root
# ---------------------------------------------------------------------------


def test_find_git_root(tmp_path):
    """Finds .git directory walking up from a subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)

    assert _find_git_root(str(subdir)) == str(tmp_path)


def test_find_git_root_at_root(tmp_path):
    """Finds .git when starting at the root itself."""
    (tmp_path / ".git").mkdir()
    assert _find_git_root(str(tmp_path)) == str(tmp_path)


def test_find_git_root_not_found(tmp_path):
    """Returns None when no .git directory exists."""
    assert _find_git_root(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# _scan_tier1
# ---------------------------------------------------------------------------


def test_tier1_discovers_claude_md(tmp_path):
    """Discovers CLAUDE.md and returns its content with header."""
    (tmp_path / "CLAUDE.md").write_text("# My Project\nPython app")

    result = _scan_tier1(str(tmp_path))

    assert result is not None
    assert "# --- from CLAUDE.md ---" in result
    assert "# My Project" in result


def test_tier1_concatenates_multiple(tmp_path):
    """Discovers and concatenates multiple context files."""
    (tmp_path / "CLAUDE.md").write_text("Claude context")
    (tmp_path / "AGENTS.md").write_text("Agents context")

    result = _scan_tier1(str(tmp_path))

    assert "# --- from CLAUDE.md ---" in result
    assert "Claude context" in result
    assert "# --- from AGENTS.md ---" in result
    assert "Agents context" in result


def test_tier1_ignores_missing(tmp_path):
    """Returns None when no Tier 1 files exist."""
    assert _scan_tier1(str(tmp_path)) is None


def test_tier1_skips_empty_files(tmp_path):
    """Skips files that exist but are empty."""
    (tmp_path / "CLAUDE.md").write_text("")
    (tmp_path / "AGENTS.md").write_text("Agents context")

    result = _scan_tier1(str(tmp_path))

    assert "CLAUDE.md" not in result
    assert "Agents context" in result


def test_tier1_discovers_nested_paths(tmp_path):
    """Discovers files in nested paths like .cursor/rules."""
    cursor_dir = tmp_path / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "rules").write_text("Cursor rules content")

    result = _scan_tier1(str(tmp_path))

    assert result is not None
    assert "# --- from .cursor/rules ---" in result
    assert "Cursor rules content" in result


def test_tier1_discovers_github_copilot(tmp_path):
    """Discovers .github/copilot-instructions.md."""
    github_dir = tmp_path / ".github"
    github_dir.mkdir()
    (github_dir / "copilot-instructions.md").write_text("Copilot instructions")

    result = _scan_tier1(str(tmp_path))

    assert result is not None
    assert "copilot-instructions.md" in result


# ---------------------------------------------------------------------------
# _scan_tier2
# ---------------------------------------------------------------------------


def test_tier2_returns_content(tmp_path):
    """Returns .eyeroll/context.md content when it exists."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    (eyeroll_dir / "context.md").write_text("# Project: myapp")

    result = _scan_tier2(str(tmp_path))

    assert result == "# Project: myapp"


def test_tier2_returns_none_when_missing(tmp_path):
    """Returns None when .eyeroll/context.md doesn't exist."""
    assert _scan_tier2(str(tmp_path)) is None


def test_tier2_warns_when_stale(tmp_path, capsys):
    """Prints warning to stderr when context is stale, but still returns content."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    (eyeroll_dir / "context.md").write_text("# Project: myapp")

    with patch("eyeroll.context._is_stale", return_value=True):
        result = _scan_tier2(str(tmp_path))

    assert result == "# Project: myapp"
    captured = capsys.readouterr()
    assert "stale" in captured.err


def test_tier2_no_warning_when_fresh(tmp_path, capsys):
    """No warning when context is fresh."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    (eyeroll_dir / "context.md").write_text("# Project: myapp")

    with patch("eyeroll.context._is_stale", return_value=False):
        result = _scan_tier2(str(tmp_path))

    assert result == "# Project: myapp"
    captured = capsys.readouterr()
    assert "stale" not in captured.err


# ---------------------------------------------------------------------------
# _is_stale
# ---------------------------------------------------------------------------


def test_is_stale_no_meta_file(tmp_path):
    """No metadata file means not stale (backward compat)."""
    assert _is_stale(str(tmp_path)) is False


def test_is_stale_newer_commit(tmp_path):
    """Stale when last git commit is newer than generated_at."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    old_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    (eyeroll_dir / "context_meta.json").write_text(
        json.dumps({"generated_at": old_time})
    )

    recent_commit = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = recent_commit

        assert _is_stale(str(tmp_path)) is True


def test_is_stale_older_commit(tmp_path):
    """Not stale when last git commit is older than generated_at."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    recent_time = datetime.now(timezone.utc).isoformat()
    (eyeroll_dir / "context_meta.json").write_text(
        json.dumps({"generated_at": recent_time})
    )

    old_commit = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = old_commit

        assert _is_stale(str(tmp_path)) is False


def test_is_stale_no_git_falls_back_to_age(tmp_path):
    """Without git, stale if older than 7 days."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    (eyeroll_dir / "context_meta.json").write_text(
        json.dumps({"generated_at": old_time})
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""

        assert _is_stale(str(tmp_path)) is True


def test_is_stale_recent_no_git(tmp_path):
    """Without git, not stale if younger than 7 days."""
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    recent_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    (eyeroll_dir / "context_meta.json").write_text(
        json.dumps({"generated_at": recent_time})
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""

        assert _is_stale(str(tmp_path)) is False


# ---------------------------------------------------------------------------
# discover_context — integration
# ---------------------------------------------------------------------------


def test_discover_context_tier1_priority(tmp_path):
    """Tier 1 files take priority over Tier 2."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "CLAUDE.md").write_text("Claude context")

    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    (eyeroll_dir / "context.md").write_text("Generated context")

    result = discover_context(cwd=str(tmp_path))

    assert "Claude context" in result
    assert "Generated context" not in result


def test_discover_context_tier2_fallback(tmp_path):
    """Falls back to Tier 2 when no Tier 1 files exist."""
    (tmp_path / ".git").mkdir()
    eyeroll_dir = tmp_path / ".eyeroll"
    eyeroll_dir.mkdir()
    (eyeroll_dir / "context.md").write_text("Generated context")

    with patch("eyeroll.context._is_stale", return_value=False):
        result = discover_context(cwd=str(tmp_path))

    assert result == "Generated context"


def test_discover_context_nothing_found(tmp_path):
    """Returns None when no context files exist anywhere."""
    result = discover_context(cwd=str(tmp_path))
    assert result is None


def test_discover_context_walks_to_git_root(tmp_path):
    """Discovers context files at git root when called from subdirectory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "CLAUDE.md").write_text("Root context")
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)

    result = discover_context(cwd=str(subdir))

    assert "Root context" in result
