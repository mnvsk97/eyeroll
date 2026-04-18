Rename an eyeroll API key.

## Usage

```
/eyeroll:keys-rename [key-id] [new-name]
```

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to run `/eyeroll:signup` first.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. If no key ID was provided, run `/eyeroll:keys-list` to show available keys and ask the user which one to rename.

4. If no new name was provided, ask the user for the new name.

5. Run:
```bash
curl -s -X PATCH "$EYEROLL_API_URL/api/keys/<KEY_ID>" \
  -H "Authorization: Bearer $EYEROLL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"<NEW_NAME>\"}"
```

6. On success, display the updated key details (id, name, masked key value).

7. On 404, tell the user the key ID wasn't found and suggest running `/eyeroll:keys-list` to see valid IDs.
