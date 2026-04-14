List all your eyeroll API keys.

## Usage

```
/eyeroll:keys-list
```

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to run `/eyeroll:signup` first.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. Run:
```bash
curl -s "$EYEROLL_API_URL/api/keys" \
  -H "Authorization: Bearer $EYEROLL_API_KEY"
```

4. Display the results as a table or list:
   - ID, Name, Key (masked: show first 8 chars + `...`), Created at

Example output:
```
ID                                    Name        Key              Created
────────────────────────────────────  ──────────  ───────────────  ──────────────────
3f2a1b...                             default     er_a1b2c3...     2026-04-14 10:22
9c8d7e...                             ci-bot      er_x9y8z7...     2026-04-15 08:01
```
