# How It Works

## Pipeline overview

```
Source (URL or file)
  |
  v
acquire.py -- Download via yt-dlp or resolve local file
  |
  v
extract.py -- Extract key frames + audio via ffmpeg
  |
  v
analyze.py -- Send frames/video/audio to vision backend
  |
  v
watch.py -- Check cache, orchestrate strategy, save intermediates
  |
  v
analyze.py -- Synthesize final report with codebase context
  |
  v
Structured markdown report
```

## Acquisition

`acquire.py` handles two cases:

- **URLs**: Downloads via yt-dlp. Supports YouTube, Loom, Vimeo, Twitter/X, and 1000+ sites. Merges to MP4. Extracts the video title from metadata.
- **Local files**: Resolves the path. Detects media type from extension.

Returns: file path, media type (`video` or `image`), title, source URL.

## Frame extraction

`extract.py` extracts key frames from videos using ffmpeg. The strategy:

1. **Extract 1 frame every 2 seconds** -- covers the full video duration
2. **Deduplicate** -- compare JPEG file sizes between consecutive frames. If the size difference is under 5KB, the frames look similar and the duplicate is dropped. This removes static periods without needing OpenCV.
3. **Enhance contrast** -- apply `eq=contrast=1.3:brightness=0.05` via ffmpeg. This helps vision models read text on screen, especially with local models.
4. **Cap at max_frames** -- if more than `max_frames` remain after dedup, evenly sample down.

A typical 30-second to 2-minute video produces 8-15 meaningful frames.

### Audio extraction

If the backend supports audio and the video has an audio track (detected via ffprobe), the audio is extracted as MP3 using ffmpeg. Silent or near-empty audio files are discarded.

## Analysis strategy

The orchestrator (`watch.py`) chooses the analysis strategy based on backend capabilities and video properties:

### Direct video upload

Used when all conditions are met:

- Backend supports video (Gemini only)
- Video is under 20MB
- Video is under 2 minutes

The full video is sent in one API call. The model sees motion, transitions, and timing.

### Frame-by-frame

Used in all other cases. Each extracted frame is analyzed individually with a structured prompt that asks for:

- Page/URL visible
- UI state and elements
- Exact text on screen
- Error messages and warnings
- User actions
- What is being demonstrated

### Parallel analysis

Frame analysis runs in parallel by default for API backends:

- **Gemini / OpenAI**: 3 concurrent workers (requests go to separate servers)
- **Ollama**: 1 worker (single GPU, concurrency adds overhead)

Override with the `--parallel` flag:

```bash
eyeroll watch video.mp4 -p 5
```

Results are sorted back into frame order after completion.

## Caching

eyeroll caches **intermediate** results, not final reports. This is a deliberate design choice.

### What gets cached

Stored in `.eyeroll/cache/<key>.json`:

- Frame-by-frame analyses (text per frame)
- Direct video analysis text
- Audio transcript
- Source URL, title, media type, timestamp

### What does NOT get cached

- The final synthesized report
- Context text or codebase context

### Why intermediates only

The expensive part is frame analysis (multiple vision API calls). The synthesis step is a single text generation call that is cheap and fast. By caching only intermediates:

- You can re-run with different `--context` without re-analyzing frames
- Codebase context changes are reflected immediately
- No stale reports -- synthesis always runs fresh

### Cache key

The cache key is a SHA-256 hash of:

- File content hash (for local files) or URL (for remote sources)
- Backend name
- Model name

Same file + same backend + same model = cache hit.

## Synthesis

The synthesis step combines all signals into a structured report. It receives:

- Frame analyses or direct video analysis
- Audio transcript
- User-provided context text
- Codebase context from `.eyeroll/context.md`

The prompt first classifies the content type (bug report, tutorial, feature demo, feature request, code review, or general notes) based on visual evidence, then adapts the analysis sections accordingly. For bug reports, evidence is categorized into confidence tiers:

### Evidence confidence tiers (bug reports)

| Tier | Meaning | Example |
|---|---|---|
| **Visible in recording** | Directly observed on screen | "Error toast reads: TypeError: Cannot read properties of undefined" |
| **Informed by codebase context** | References real files from the project | "In `src/checkout/handler.py` (from codebase context), the `process_payment` function..." |
| **Hypothesis** | Educated guess, not confirmed | "The user object may not have a Stripe customer ID, which would cause this error" |

This tiered approach prevents the coding agent from treating guesses as facts. Without codebase context, all file paths are explicitly labeled as hypotheses.

### Content-adaptive suggestions

The report's suggested next steps adapt to the content type:

- **Bug report** → investigate and fix, raise a PR
- **Tutorial** → create a reusable skill or automation
- **Feature demo** → document, create notes
- **Feature request** → spec it out, create tasks

## Supported inputs

| Type | Formats |
|---|---|
| **Video** | .mp4, .webm, .mov, .avi, .mkv, .flv, .ts, .m4v, .wmv, .3gp, .mpg, .mpeg |
| **Image** | .png, .jpg, .jpeg, .gif, .webp, .bmp, .tiff, .heic, .avif |
| **URL** | YouTube, Loom, Vimeo, Twitter/X, Reddit, and 1000+ sites via yt-dlp |
