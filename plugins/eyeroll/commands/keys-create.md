Create a new eyeroll API key.

## Usage

```
/eyeroll:keys-create [name]
```

If no name is given, ask the user what to call the key (e.g. "ci-bot", "laptop", "production").

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to run `/eyeroll:signup` first.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. Determine the key name: use the argument if provided, otherwise ask the user.

4. Run:
```bash
curl -s -X POST "$EYEROLL_API_URL/api/keys" \
  -H "Authorization: Bearer $EYEROLL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"<NAME>\"}"
```

5. Display the new key clearly:
   - **API key**: `api_key` value (shown in full — this is the only time it's shown)
   - **Key ID**: `key_id`
   - **Name**: `key_name`

6. Remind the user: this key has the same permissions and rate limit as their existing keys. Use `/eyeroll:keys-list` to see all keys.
