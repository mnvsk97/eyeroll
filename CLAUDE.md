# CLAUDE.md

## Project

reelfix — Watch a bug video, understand it, map it to code, fix it. Takes video URLs (Loom, YouTube), local video files, or screenshots as input. Uses Gemini Flash for vision analysis and audio transcription. Produces structured bug reports that coding agents can use to find relevant code and raise PRs.

## Commands

```bash
# Install
pip install .
# or with uv:
uv sync

# Run tests
pytest
pytest --cov --cov-report=term-missing

# CLI
reelfix init                                              # set up Gemini API key
reelfix watch <url-or-path>                               # analyze a video/screenshot
reelfix watch <url> --context "broken after PR #432"      # with reporter context
reelfix watch <path> --verbose --output report.md         # verbose + write to file
```

## Architecture

- **Pipeline**: `acquire.py` (download/locate) → `extract.py` (frames + audio) → `analyze.py` (Gemini vision + synthesis) → `watch.py` (orchestrator)
- **acquire.py**: Downloads from URLs via yt-dlp, resolves local files. Returns file_path, media_type, title.
- **extract.py**: ffmpeg wrappers for key frame extraction, audio extraction, duration detection. Falls back to imageio-ffmpeg.
- **analyze.py**: Gemini Flash API calls. Frame-by-frame analysis with structured prompts, direct video upload for short videos, audio transcription, and synthesis into bug report.
- **watch.py**: Orchestrates the full pipeline. Chooses strategy (direct upload vs frame-by-frame) based on video size/duration. Handles cleanup.
- **cli.py**: Click CLI with `init` and `watch` commands.

## Key design decisions

- **Single backend (Gemini Flash)**: Intentionally simple. One API key, one set of failure modes. Gemini handles video, images, and audio natively.
- **Direct upload vs frame-by-frame**: Videos under 20MB/2min are sent whole to Gemini (better context). Longer videos use frame extraction.
- **Context text is critical**: Most bug videos are silent screen recordings. The reporter's Slack message or issue description often contains more intent than the video itself.
- **No codebase mapping in the skill itself**: The skill produces a bug report. Claude Code (which has codebase context) handles finding relevant code and implementing fixes.

## Testing patterns

- Mock all Gemini API calls in tests — never hit external services.
- Use synthetic test videos generated via ffmpeg fixtures.
- Test acquire.py with both URL and local file paths.
