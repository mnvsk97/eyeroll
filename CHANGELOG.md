# Changelog

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
