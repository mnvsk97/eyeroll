# /eyeroll:history

List and manage past video analyses from the cache.

## Usage

```
/eyeroll:history
/eyeroll:history clear
```

## Listing analyses

```
/eyeroll:history
```

Output:

```
[2025-12-15 14:30] https://loom.com/share/abc123 (video (00:45)) -- 123a284dacc6a103
[2025-12-15 10:15] ./bug.mp4 (video (01:22)) -- e086216d2028cfa8
[2025-12-14 09:00] ./screenshot.png (screenshot) -- 4ebf8366855cd994
```

Each entry shows: timestamp, source, media type, and cache key.

## Limiting results

```
/eyeroll:history --limit 5
```

Shows only the 5 most recent analyses.

## JSON output

```
/eyeroll:history --json
```

Returns structured JSON for programmatic use:

```json
[
  {
    "source": "https://loom.com/share/abc123",
    "timestamp": "2025-12-15T14:30:00+00:00",
    "key": "123a284dacc6a103",
    "media_type": "video (00:45)",
    "title": "Bug recording"
  }
]
```

## Clearing the cache

```
/eyeroll:history clear
```

Removes all cached analyses from `.eyeroll/cache/`. Prompts for confirmation unless `--yes` is passed.

```bash
# Skip confirmation
eyeroll history clear --yes
```

## Re-watching cached videos

If you re-watch a video that has cached intermediates, eyeroll skips the expensive frame analysis and re-runs only the synthesis step. This means you can provide new `--context` for free:

```
/eyeroll:watch ./bug.mp4 --context "actually this might be a CORS issue"
```

This is instant because the frame analyses and transcripts are already cached.

## CLI equivalent

```bash
eyeroll history                  # list all
eyeroll history --limit 5       # last 5
eyeroll history --json           # JSON output
eyeroll history clear            # clear cache
eyeroll history clear --yes      # clear without confirmation
```
