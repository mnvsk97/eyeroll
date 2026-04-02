"""Tests for the history module."""

import json
import os

import pytest

from eyeroll.history import clear_history, get_cached_entry, list_history


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Set up a temporary cache directory."""
    cache = tmp_path / ".eyeroll" / "cache"
    cache.mkdir(parents=True)
    monkeypatch.setattr("eyeroll.history.CACHE_DIR", str(cache))
    return cache


def _write_entry(cache_dir, key, source, timestamp, **extra):
    """Helper to write a cache entry (metadata JSON + report MD)."""
    meta = {"key": key, "source": source, "timestamp": timestamp, **extra}
    with open(cache_dir / f"{key}.json", "w") as f:
        json.dump(meta, f)
    with open(cache_dir / f"{key}.md", "w") as f:
        f.write(f"# Report for {source}\n\nSome content.")


# ---------------------------------------------------------------------------
# list_history
# ---------------------------------------------------------------------------


def test_list_history_empty(cache_dir):
    """Empty cache returns empty list."""
    result = list_history()
    assert result == []


def test_list_history_returns_sorted(cache_dir):
    """Entries are returned sorted by timestamp descending (newest first)."""
    _write_entry(cache_dir, "aaa111", "video1.mp4", "2024-01-15T13:00:00+00:00")
    _write_entry(cache_dir, "bbb222", "https://loom.com/share/xyz", "2024-01-15T14:30:00+00:00")
    _write_entry(cache_dir, "ccc333", "demo.mp4", "2024-01-14T10:00:00+00:00")

    result = list_history()

    assert len(result) == 3
    assert result[0]["key"] == "bbb222"  # newest
    assert result[1]["key"] == "aaa111"
    assert result[2]["key"] == "ccc333"  # oldest


def test_list_history_with_limit(cache_dir):
    """Limit restricts the number of results."""
    _write_entry(cache_dir, "aaa111", "video1.mp4", "2024-01-15T13:00:00+00:00")
    _write_entry(cache_dir, "bbb222", "video2.mp4", "2024-01-15T14:30:00+00:00")
    _write_entry(cache_dir, "ccc333", "video3.mp4", "2024-01-14T10:00:00+00:00")

    result = list_history(limit=2)

    assert len(result) == 2
    assert result[0]["key"] == "bbb222"
    assert result[1]["key"] == "aaa111"


def test_list_history_handles_new_format(cache_dir):
    """New format with title and media_type is preserved."""
    _write_entry(
        cache_dir, "ddd444", "video.mp4", "2024-01-16T09:00:00+00:00",
        title="My Video", media_type="video",
    )

    result = list_history()

    assert len(result) == 1
    assert result[0]["title"] == "My Video"
    assert result[0]["media_type"] == "video"


def test_list_history_skips_corrupt_json(cache_dir):
    """Corrupt JSON files are silently skipped."""
    _write_entry(cache_dir, "aaa111", "video1.mp4", "2024-01-15T13:00:00+00:00")
    # Write a corrupt JSON file
    with open(cache_dir / "corrupt.json", "w") as f:
        f.write("{bad json")

    result = list_history()
    assert len(result) == 1


def test_list_history_nonexistent_dir(monkeypatch):
    """Non-existent cache dir returns empty list."""
    monkeypatch.setattr("eyeroll.history.CACHE_DIR", "/nonexistent/path")
    result = list_history()
    assert result == []


# ---------------------------------------------------------------------------
# get_cached_entry
# ---------------------------------------------------------------------------


def test_get_cached_entry(cache_dir):
    """Returns the metadata dict for a valid key."""
    _write_entry(cache_dir, "aaa111", "video.mp4", "2024-01-15T13:00:00+00:00")

    entry = get_cached_entry("aaa111")

    assert entry is not None
    assert entry["source"] == "video.mp4"
    assert entry["key"] == "aaa111"


def test_get_cached_entry_missing(cache_dir):
    """Returns None for a non-existent key."""
    entry = get_cached_entry("nonexistent")
    assert entry is None


# ---------------------------------------------------------------------------
# clear_history
# ---------------------------------------------------------------------------


def test_clear_history(cache_dir):
    """Clears all files from the cache directory."""
    _write_entry(cache_dir, "aaa111", "video1.mp4", "2024-01-15T13:00:00+00:00")
    _write_entry(cache_dir, "bbb222", "video2.mp4", "2024-01-15T14:30:00+00:00")

    assert len(os.listdir(cache_dir)) == 4  # 2 .json + 2 .md

    clear_history()

    assert len(os.listdir(cache_dir)) == 0


def test_clear_history_empty(cache_dir):
    """Clearing an empty cache does nothing."""
    clear_history()  # should not raise
    assert len(os.listdir(cache_dir)) == 0


def test_clear_history_nonexistent_dir(monkeypatch):
    """Clearing a non-existent dir does nothing."""
    monkeypatch.setattr("eyeroll.history.CACHE_DIR", "/nonexistent/path")
    clear_history()  # should not raise
