Check how many eyeroll analyses you have used today and when your limit resets.

## Usage

```
/eyeroll:api-usage
```

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to get a key at `https://api.eyeroll.dev`.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. Run:
```bash
curl -s "$EYEROLL_API_URL/api/usage" \
  -H "Authorization: Bearer $EYEROLL_API_KEY"
```

4. Display the result in a clear format, e.g.:
   - Used today: N / 20
   - Resets at: <reset_at>
