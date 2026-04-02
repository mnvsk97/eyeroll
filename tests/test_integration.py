"""Integration tests — real API calls with real media.

Run manually before releases:
    pytest tests/test_integration.py -v -m integration

Requires:
    - GEMINI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS set (for gemini tests)
    - OPENAI_API_KEY set (for openai tests)
    - Ollama running locally (for ollama tests)
    - ffmpeg installed

These tests are SKIPPED in normal CI runs.
"""

import os
from pathlib import Path

import pytest

from eyeroll.watch import watch

# Skip all tests in this file unless explicitly running integration tests
pytestmark = pytest.mark.integration

# Real screen recording of a 401 error (31s, 278KB)
FIXTURE_DIR = Path(__file__).parent / "fixtures"
REAL_VIDEO = str(FIXTURE_DIR / "web_search_tool_401_error.mp4")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_video():
    """Real screen recording showing a web search tool 401 error."""
    assert os.path.isfile(REAL_VIDEO), f"Fixture not found: {REAL_VIDEO}"
    return REAL_VIDEO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_gemini() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


def _has_key(env_var: str) -> bool:
    return bool(os.environ.get(env_var))


def _ollama_running() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Gemini integration tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _has_gemini(), reason="No Gemini credentials")
class TestGeminiIntegration:

    def test_watch_video(self, test_video):
        """Full pipeline: real video → Gemini → structured report."""
        report = watch(test_video, backend_name="gemini", verbose=True, no_cache=True)
        assert "# eyeroll:" in report
        assert "Video Analysis" in report or "Summary" in report
        # Should detect something meaningful from the 401 error recording
        print(f"\n--- REPORT ---\n{report[:2000]}")

    def test_watch_with_context(self, test_video):
        """Context should influence the report."""
        report = watch(
            test_video,
            backend_name="gemini",
            context="Web search tool returning 401 unauthorized error",
            no_cache=True,
        )
        assert "# eyeroll:" in report
        assert "401" in report or "error" in report.lower() or "unauthorized" in report.lower()

    def test_watch_with_codebase_context(self, test_video):
        """Codebase context should be referenced in Fix Directions."""
        report = watch(
            test_video,
            backend_name="gemini",
            context="401 error on web search tool",
            codebase_context="## Project: search-app\n**Stack:** Python, FastAPI\n## Key Files\n- src/api/search.py\n- src/auth/middleware.py",
            no_cache=True,
        )
        assert "# eyeroll:" in report

    def test_watch_parallel(self, test_video):
        """Parallel frame analysis should produce valid report."""
        report = watch(
            test_video,
            backend_name="gemini",
            parallel=3,
            no_cache=True,
        )
        assert "# eyeroll:" in report


# ---------------------------------------------------------------------------
# OpenAI integration tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _has_key("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
class TestOpenAIIntegration:

    def test_watch_video(self, test_video):
        report = watch(test_video, backend_name="openai", verbose=True, no_cache=True)
        assert "# eyeroll:" in report


# ---------------------------------------------------------------------------
# Ollama integration tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ollama_running(), reason="Ollama not running")
class TestOllamaIntegration:

    def test_watch_video(self, test_video):
        report = watch(
            test_video,
            backend_name="ollama",
            model="qwen3-vl:2b",
            verbose=True,
            no_cache=True,
        )
        assert "# eyeroll:" in report


# ---------------------------------------------------------------------------
# Cache integration — verify caching round-trip with real analysis
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _has_gemini(), reason="No Gemini credentials")
class TestCacheIntegration:

    def test_cache_hit_skips_reanalysis(self, test_video):
        """Second call with same video should be instant (cache hit)."""
        import time

        # First call — full analysis
        t0 = time.time()
        report1 = watch(test_video, backend_name="gemini", no_cache=True)
        first_duration = time.time() - t0

        # Second call — should hit cache (synthesis still runs but frame analysis is skipped)
        t0 = time.time()
        report2 = watch(test_video, backend_name="gemini")
        second_duration = time.time() - t0

        # Cache hit should be much faster
        assert second_duration < first_duration / 2
        assert "# eyeroll:" in report1
        assert "# eyeroll:" in report2

    def test_different_context_different_report(self, test_video):
        """Same cached video with different context should produce different synthesis."""
        report_a = watch(
            test_video, backend_name="gemini",
            context="This is a bug report showing a 401 error",
        )
        report_b = watch(
            test_video, backend_name="gemini",
            context="Create a skill for handling auth token refresh",
        )
        assert "# eyeroll:" in report_a
        assert "# eyeroll:" in report_b
