# Development

## Getting started

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
pip install -e '.[dev,all]'
```

Or with uv:

```bash
git clone https://github.com/mnvsk97/eyeroll.git
cd eyeroll
uv sync
```

## Running tests

```bash
# Unit tests (143 tests, mocked -- no API calls)
pytest

# With coverage
pytest --cov --cov-report=term-missing

# Integration tests (real API calls -- requires credentials)
pytest tests/test_integration.py -v -m integration
```

!!! warning "Integration tests"
    Integration tests hit real APIs and download real videos. They require valid API keys and are skipped by default in CI. Run them manually before releases.

## Test patterns

- All API calls, Ollama calls, ffmpeg, and yt-dlp are mocked in unit tests
- Synthetic test videos are generated via ffmpeg fixtures in `conftest.py`
- `acquire.py` is tested with both URL and local file paths
- Backend tests verify the abstract interface and each implementation

## Project structure

```
eyeroll/
  __init__.py
  acquire.py          # Download from URLs, resolve local files
  extract.py          # ffmpeg: key frame extraction, audio extraction
  analyze.py          # Backend-agnostic analysis, synthesis prompts
  backend.py          # Backend ABC + Gemini, OpenAI, Ollama implementations
  watch.py            # Pipeline orchestrator, caching
  history.py          # Cache listing, retrieval, clearing
  cli.py              # Click CLI (init, watch, history)

commands/             # Claude Code slash commands
  init.md             # /eyeroll:init
  watch.md            # /eyeroll:watch
  fix.md              # /eyeroll:fix
  history.md          # /eyeroll:history

skills/               # Background skills
  video-to-skill/     # Activated by "create a skill from this video"

tests/
  conftest.py         # Shared fixtures
  test_acquire.py
  test_analyze.py
  test_backend.py
  test_cli.py
  test_extract.py
  test_history.py
  test_watch.py
  test_integration.py # Real API tests (marked, skipped by default)
```

## CI/CD

A single GitHub Actions workflow (`.github/workflows/ci.yml`) handles both testing and publishing:

**Testing**: Runs on every push to `main` and `feat/**` branches, and on all pull requests. Tests against Python 3.11, 3.12, and 3.13.

**Publishing**: On push to `main`, builds the package and publishes to PyPI if the version does not already exist. Uses trusted publishing (OIDC) -- no API tokens stored.

## Key design decisions

**Backend abstraction**: The `Backend` ABC defines `analyze_image`, `analyze_video`, `analyze_audio`, and `generate`. Each backend declares its capabilities via `supports_video` and `supports_audio` properties. The orchestrator uses these to choose the right strategy.

**Cache intermediates, not reports**: The expensive operations are frame analysis and audio transcription. Synthesis is cheap. Caching intermediates lets users re-run with different context without re-analyzing.

**Confidence tiers in Fix Directions**: Every claim in the report is categorized as directly observed, informed by codebase context, or hypothesis. This prevents coding agents from hallucinating file paths.

**No OpenCV**: Frame deduplication uses JPEG file size comparison instead of perceptual hashing. This avoids a heavy dependency while being good enough for screen recordings where static frames compress similarly.

## Build

eyeroll uses [hatchling](https://hatch.pypa.io/) as the build backend:

```bash
pip install build
python -m build
```

## Release checklist

1. Bump version in `pyproject.toml`
2. Run full test suite: `pytest`
3. Run integration tests: `pytest tests/test_integration.py -v -m integration`
4. Push to `main` -- CI publishes to PyPI automatically
