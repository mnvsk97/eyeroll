Analyze a video URL or local file using the eyeroll hosted API.

## Usage

```
/eyeroll:api-watch <url-or-path> [context]
```

## What this does

1. Reads `EYEROLL_API_KEY` and `EYEROLL_API_URL` from the environment
2. POSTs the source and optional context to `/api/watch`
3. Returns the structured markdown report

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to get a key at `$EYEROLL_API_URL` (or `https://api.eyeroll.dev`) and set it.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. Run:
```bash
curl -s -X POST "$EYEROLL_API_URL/api/watch" \
  -H "Authorization: Bearer $EYEROLL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"source\": \"$ARGUMENTS\", \"context\": null}"
```

4. Parse the `report` field from the JSON response and print it as markdown.

5. If the response status is 429, tell the user their daily limit is reached and show the `reset_at` time.

6. If the response status is 401, tell the user their API key is invalid.
