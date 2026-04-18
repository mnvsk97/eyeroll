"""Auto-discover codebase context from known context files.

Tier 1: Files maintained by coding tools (CLAUDE.md, AGENTS.md, etc.)
        Always fresh — the tools that own them keep them updated.

Tier 2: Generated .eyeroll/context.md (fallback when no Tier 1 files exist).
        May go stale — staleness is checked via .eyeroll/context_meta.json.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Files maintained by coding tools — always current
TIER1_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    ".cursorrules",
    ".cursor/rules",
    "codex.md",
    ".github/copilot-instructions.md",
    "CONVENTIONS.md",
    "ARCHITECTURE.md",
]

TIER2_FILE = os.path.join(".eyeroll", "context.md")
TIER2_META = os.path.join(".eyeroll", "context_meta.json")


def discover_context(cwd: str | None = None) -> str | None:
    """Auto-discover codebase context from known files.

    Checks Tier 1 files first (coding tool context), then falls back
    to Tier 2 (generated .eyeroll/context.md).

    Args:
        cwd: Directory to search from. Defaults to os.getcwd().
             Walks up to git root if in a git repo.

    Returns:
        Concatenated context string, or None if nothing found.
    """
    if cwd is None:
        cwd = os.getcwd()

    root = _find_git_root(cwd) or cwd

    context = _scan_tier1(root)
    if context:
        return context

    return _scan_tier2(root)


def _find_git_root(start: str) -> str | None:
    """Walk up from start directory to find the git root."""
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _scan_tier1(root: str) -> str | None:
    """Scan for context files maintained by coding tools.

    Returns concatenated content with source headers, or None if none found.
    """
    parts = []
    for filename in TIER1_FILES:
        filepath = os.path.join(root, filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath) as f:
                    content = f.read().strip()
                if content:
                    parts.append(f"# --- from {filename} ---\n{content}")
            except OSError:
                continue

    if not parts:
        return None
    return "\n\n".join(parts)


def _scan_tier2(root: str) -> str | None:
    """Check for generated .eyeroll/context.md, with staleness warning.

    Returns content or None. Warns to stderr if stale.
    """
    filepath = os.path.join(root, TIER2_FILE)
    if not os.path.isfile(filepath):
        return None

    try:
        with open(filepath) as f:
            content = f.read().strip()
    except OSError:
        return None

    if not content:
        return None

    if _is_stale(root):
        print(
            "  Warning: .eyeroll/context.md may be stale. "
            "Run /eyeroll:init to regenerate.",
            file=sys.stderr,
        )

    return content


def _is_stale(root: str) -> bool:
    """Check if generated context is older than the latest repo activity.

    Reads .eyeroll/context_meta.json for the generation timestamp.
    Compares against the last git commit time, or falls back to 7-day age check.
    """
    meta_path = os.path.join(root, TIER2_META)
    if not os.path.isfile(meta_path):
        return False  # no metadata = unknown age, assume not stale

    try:
        with open(meta_path) as f:
            meta = json.load(f)
        generated_at = datetime.fromisoformat(meta["generated_at"])
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return False

    # Compare against last git commit
    try:
        result = subprocess.run(
            ["git", "-C", root, "log", "-1", "--format=%cI"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            last_commit = datetime.fromisoformat(result.stdout.strip())
            return last_commit > generated_at
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    # Fallback: stale if older than 7 days
    age = datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)
    return age.days > 7
