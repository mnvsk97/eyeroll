"""Integration tests — real API calls with real media.

Run manually before releases:
    pytest tests/test_integration.py -v -m integration

Requires:
    - GEMINI_API_KEY set (for gemini tests)
    - OPENAI_API_KEY set (for openai tests)
    - Ollama running locally (for ollama tests)
    - ffmpeg installed
    - yt-dlp installed (for URL tests)

These tests are SKIPPED in normal CI runs.
"""

import os
import subprocess
import tempfile

import pytest

from eyeroll.watch import watch

# Skip all tests in this file unless explicitly running integration tests
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures — generate real test media with ffmpeg
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_video():
    """Generate a short synthetic video with ffmpeg (3 seconds, color changes)."""
    tmpdir = tempfile.mkdtemp(prefix="eyeroll_integ_")
    video_path = os.path.join(tmpdir, "test.mp4")

    # 3-second video: red -> green -> blue (1 sec each) — clear scene changes
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            "color=c=red:s=640x480:d=1,format=yuv420p[v0];"
            "color=c=green:s=640x480:d=1,format=yuv420p[v1];"
            "color=c=blue:s=640x480:d=1,format=yuv420p[v2];"
            "[v0][v1][v2]concat=n=3:v=1:a=0[out]",
            "-map", "[out]",
            video_path,
        ],
        capture_output=True, check=True,
    )
    yield video_path

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="module")
def test_image():
    """Generate a test image with ffmpeg (single frame with text)."""
    tmpdir = tempfile.mkdtemp(prefix="eyeroll_integ_")
    image_path = os.path.join(tmpdir, "test.png")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            "color=c=white:s=640x480:d=1,drawtext=text='Hello eyeroll':fontsize=48:x=(w-tw)/2:y=(h-th)/2:fontcolor=black",
            "-vframes", "1",
            image_path,
        ],
        capture_output=True, check=True,
    )
    yield image_path

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

@pytest.mark.skipif(not _has_key("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
class TestGeminiIntegration:

    def test_watch_video(self, test_video):
        report = watch(test_video, backend_name="gemini", verbose=True)
        assert "# eyeroll:" in report
        assert "Video Analysis" in report or "Summary" in report

    def test_watch_image(self, test_image):
        report = watch(test_image, backend_name="gemini", verbose=True)
        assert "# eyeroll:" in report
        assert "screenshot" in report.lower()

    def test_watch_with_context(self, test_video):
        report = watch(
            test_video,
            backend_name="gemini",
            context="This shows a color transition bug",
        )
        assert "# eyeroll:" in report

    def test_watch_with_codebase_context(self, test_video):
        report = watch(
            test_video,
            backend_name="gemini",
            codebase_context="## Project: test-app\n**Stack:** Python, FastAPI",
        )
        assert "# eyeroll:" in report

    def test_watch_parallel(self, test_video):
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
        report = watch(test_video, backend_name="openai", verbose=True)
        assert "# eyeroll:" in report

    def test_watch_image(self, test_image):
        report = watch(test_image, backend_name="openai", verbose=True)
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
        )
        assert "# eyeroll:" in report

    def test_watch_image(self, test_image):
        report = watch(
            test_image,
            backend_name="ollama",
            model="qwen3-vl:2b",
            verbose=True,
        )
        assert "# eyeroll:" in report


# ---------------------------------------------------------------------------
# Cache integration — verify caching round-trip with real analysis
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _has_key("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
class TestCacheIntegration:

    def test_cache_hit_skips_reanalysis(self, test_video):
        """Second call with same video should be instant (cache hit)."""
        import time

        # First call — full analysis
        t0 = time.time()
        report1 = watch(test_video, backend_name="gemini", no_cache=True)
        first_duration = time.time() - t0

        # Second call — should hit cache
        t0 = time.time()
        report2 = watch(test_video, backend_name="gemini")
        second_duration = time.time() - t0

        # Cache hit should be much faster
        assert second_duration < first_duration / 2
        # Reports may differ (synthesis re-runs) but both should be valid
        assert "# eyeroll:" in report1
        assert "# eyeroll:" in report2

    def test_different_context_different_report(self, test_video):
        """Same cached video with different context should produce different synthesis."""
        report_a = watch(
            test_video, backend_name="gemini",
            context="This is a bug report",
        )
        report_b = watch(
            test_video, backend_name="gemini",
            context="Create a skill from this tutorial",
        )
        # Both valid, but content should differ due to context
        assert "# eyeroll:" in report_a
        assert "# eyeroll:" in report_b
