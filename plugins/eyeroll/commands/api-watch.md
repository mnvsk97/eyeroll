Analyze a video URL or local file using the eyeroll hosted API.

## Usage

```
/eyeroll:api-watch <url-or-path> [context]
```

## What this does

1. Reads `EYEROLL_API_URL` from the environment, defaulting to the hosted API URL
2. POSTs the source and optional context to `/api/watch`
3. Returns intent, repo guess, handoff recommendation, confidence, and the structured markdown report

## Steps

1. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

2. Call the hosted API. Authentication is handled by the deployment platform, not by eyeroll API keys.

3. Run:
```bash
curl -s -X POST "$EYEROLL_API_URL/api/watch" \
  -H "Content-Type: application/json" \
  -d "{\"source\": \"$ARGUMENTS\", \"context\": null}"
```

4. Display the structured response:
   - intent
   - repo_guess
   - handoff_recommended
   - confidence
   - report

5. If the response status is 401 or 403, tell the user the hosted endpoint authentication is blocking the request and they should authenticate through the TrueFoundry-protected route.
