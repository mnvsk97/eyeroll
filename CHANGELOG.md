# Changelog

## 0.5.0

- **Auto-discover codebase context**: Automatically finds CLAUDE.md, AGENTS.md, .cursorrules, codex.md, and other coding tool context files at watch-time. No more manual `--codebase-context` needed.
- **Global cache**: Cache moved to `~/.eyeroll/cache/` — same video analyzed from any project reuses cached analysis. URLs are now content-hashed (same video via different links = cache hit).
- **Gemini 2.5-flash**: Default model upgraded from 2.0-flash to 2.5-flash
- **Whisper confidence filtering**: Low-confidence audio segments are dropped. `--min-audio-confidence` flag (default 0.4). Warns when audio quality is poor.
- **Scene-change frame detection**: PIL-based pixel-diff for smarter frame extraction. `--scene-threshold` flag (default 0 = existing behavior, set to 30.0 to enable).
- **Frame context chaining**: Sequential frame analysis passes previous frame's summary to the next frame's prompt for better continuity.
- **Cost estimates**: Prints estimated cost to stderr after analysis. `--no-cost` flag to suppress. Ollama always shows $0.00.
- **New flags**: `--no-context`, `--no-cost`, `--min-audio-confidence`, `--scene-threshold`
- **Pillow** added as core dependency (for scene-change detection)
- Removed Ollama auto-install — users install Ollama themselves
- Staleness tracking for generated `.eyeroll/context.md` via `context_meta.json`
- Plugin commands no longer hardcode `--codebase-context .eyeroll/context.md`

## 0.3.4

- OSS readiness: code cleanup, docs consistency, contributor tooling
- Add GitHub issue templates and PR template
- Add CI, PyPI, Python version, and license badges to README
- Unify plugin install commands to marketplace format across all docs
- Fix project structure paths in development docs
- Extract duplicated MIME map, remove dead code, clean up imports
- Add Ollama qwen3-vl:8b known limitations to docs
- Bump status from Alpha to Beta

## 0.3.3

- Content-adaptive synthesis: detects bug/demo/tutorial/feature-request/code-review and adapts report sections
- Smart parallel defaults based on frame count

## 0.3.2

- Fix plugin registration: add commands and skills to plugin.json
- Clean up fix command
- Make video-to-skill invocable

## 0.3.1

- OpenAI backend: GPT-4o for frame analysis, Whisper for audio transcription
- Intermediate caching: same video + different context = instant re-synthesis
- History command: list past video analyses

## 0.3.0

- Parallel frame analysis with `--parallel` flag
- Codebase context via `.eyeroll/context.md`
- Fix command: watch video, diagnose, fix code, raise PR

## 0.2.0

- Ollama backend with Qwen3-VL support
- Auto-install Ollama and pull models
- Frame deduplication via JPEG size comparison
- Contrast enhancement for screen recordings

## 0.1.0

- Initial release
- Gemini Flash backend with direct video upload
- Frame extraction (1 per 2s) via ffmpeg
- Audio transcription
- Structured bug reports
- CLI with `init` and `watch` commands
