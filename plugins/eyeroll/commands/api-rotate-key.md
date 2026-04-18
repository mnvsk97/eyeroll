Rotate your eyeroll API key. The current key is immediately invalidated and a new one is returned.

## Usage

```
/eyeroll:api-rotate-key
```

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to get a key at `https://api.eyeroll.dev`.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. Confirm with the user before rotating, since the old key will immediately stop working.

4. Run:
```bash
curl -s -X POST "$EYEROLL_API_URL/api/keys/rotate" \
  -H "Authorization: Bearer $EYEROLL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

5. Display the new key clearly and remind the user to update `EYEROLL_API_KEY` in their shell profile and any `.env` files.
