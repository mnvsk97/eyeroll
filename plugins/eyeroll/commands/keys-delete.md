Revoke (permanently delete) an eyeroll API key.

## Usage

```
/eyeroll:keys-delete [key-id]
```

## Steps

1. Check that `$EYEROLL_API_KEY` is set. If not, tell the user to run `/eyeroll:signup` first.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set.

3. If no key ID was provided as an argument, run `/eyeroll:keys-list` first to show the user their keys, then ask them which ID to delete.

4. Confirm with the user before deleting — this cannot be undone.

5. Run:
```bash
curl -s -X DELETE "$EYEROLL_API_URL/api/keys/<KEY_ID>" \
  -H "Authorization: Bearer $EYEROLL_API_KEY"
```

6. On success (204 No Content), confirm the key has been revoked.

7. On 400 error ("Cannot delete the last API key"), tell the user to create a new key first with `/eyeroll:keys-create`, then delete the old one.

8. Remind the user: if they deleted the key stored in `$EYEROLL_API_KEY`, they need to update that env var with another active key from `/eyeroll:keys-list`.
