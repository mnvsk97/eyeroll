"""History module — list, retrieve, and clear cached analyses."""

import json
import os
import glob as glob_mod

CACHE_DIR = os.path.join(".eyeroll", "cache")


def list_history(limit: int | None = None) -> list[dict]:
    """Read all .json metadata files from the cache, sorted by timestamp descending.

    Works with both old format (source, timestamp, key) and new format
    (source, timestamp, key, title, media_type, frame_analyses, ...).

    Returns:
        List of metadata dicts, newest first.
    """
    if not os.path.isdir(CACHE_DIR):
        return []

    entries = []
    for meta_path in glob_mod.glob(os.path.join(CACHE_DIR, "*.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            # Ensure required fields exist
            if "key" in meta and "timestamp" in meta:
                entries.append(meta)
        except (json.JSONDecodeError, OSError):
            continue

    # Sort by timestamp descending
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    if limit is not None:
        entries = entries[:limit]

    return entries


def get_cached_entry(key: str) -> dict | None:
    """Load a cached entry by its cache key.

    Returns the full metadata dict (including intermediates like
    frame_analyses, video_analysis, transcript) or None if not found.
    """
    meta_path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def clear_history() -> None:
    """Delete all files in the cache directory."""
    if not os.path.isdir(CACHE_DIR):
        return

    for filepath in glob_mod.glob(os.path.join(CACHE_DIR, "*")):
        try:
            os.remove(filepath)
        except OSError:
            continue
