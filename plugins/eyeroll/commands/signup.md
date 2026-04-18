Sign up for eyeroll and get your first free API key.

## Usage

```
/eyeroll:signup
```

## Steps

1. Ask the user for their email address if it wasn't provided as an argument.

2. Set `EYEROLL_API_URL` to `https://api.eyeroll.dev` if not already set in the environment.

3. Call the signup endpoint:
```bash
curl -s -X POST "$EYEROLL_API_URL/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"<EMAIL>\"}"
```

4. On success, display the result clearly:
   - **API key**: the `api_key` value (this is the bearer token)
   - **Key ID**: `key_id` (used to manage this key later)
   - **Key name**: `key_name`

5. Tell the user to save the key and set these environment variables:
```bash
export EYEROLL_API_KEY=<api_key>
export EYEROLL_API_URL=https://api.eyeroll.dev
```
   Suggest adding them to `~/.zshrc`, `~/.bashrc`, or their project `.env`.

6. Confirm: once `EYEROLL_API_KEY` is set, `eyeroll watch <url>` will automatically use the hosted API — no Gemini or OpenAI key needed.

7. Note: calling `/eyeroll:signup` again with the same email is safe — it returns the existing account's key without creating duplicates.
