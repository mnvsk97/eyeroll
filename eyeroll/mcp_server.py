"""eyeroll MCP server — stdio transport.

Tools
-----
  signup         POST /signup            — create account, get first API key
  watch_video    POST /api/watch         — analyze a video
  check_usage    GET  /api/usage         — daily limit check
  keys_list      GET  /api/keys          — list all keys
  keys_create    POST /api/keys          — create a new key
  keys_rename    PATCH /api/keys/{id}    — rename a key
  keys_delete    DELETE /api/keys/{id}   — revoke a key

Configuration (env vars):
  EYEROLL_API_KEY  Your eyeroll API key (required for authenticated tools)
  EYEROLL_API_URL  API base URL (default: https://api.eyeroll.dev)

Run:
  python -m eyeroll.mcp_server
  # or after pip install:
  eyeroll-mcp
"""

import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), ".eyeroll", ".env"))
load_dotenv()


def _base_url() -> str:
    return os.environ.get("EYEROLL_API_URL", "https://api.eyeroll.dev").rstrip("/")


def _api_key() -> str:
    key = os.environ.get("EYEROLL_API_KEY", "")
    if not key:
        raise RuntimeError("EYEROLL_API_KEY is not set. Run the signup tool first.")
    return key


def _request(method: str, path: str, body: dict | None = None, *, auth: bool = True) -> dict:
    url = f"{_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {_api_key()}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body_text).get("detail", body_text)
        except Exception:
            detail = body_text
        raise RuntimeError(f"API error {exc.code}: {detail}") from exc


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_signup(email: str) -> str:
    result = _request("POST", "/signup", {"email": email}, auth=False)
    lines = [
        f"Account created (or already exists) for {email}",
        "",
        f"API key : {result['api_key']}",
        f"Key ID  : {result['key_id']}",
        f"Name    : {result['key_name']}",
        "",
        "Set in your environment:",
        f"  export EYEROLL_API_KEY={result['api_key']}",
        f"  export EYEROLL_API_URL={_base_url()}",
    ]
    return "\n".join(lines)


def _tool_watch_video(source: str, context: str | None = None, max_frames: int = 20) -> str:
    result = _request("POST", "/api/watch", {
        "source": source,
        "context": context,
        "max_frames": max_frames,
    })
    return result["report"]


def _tool_check_usage() -> str:
    r = _request("GET", "/api/usage")
    return f"Used today: {r['used_today']} / {r['limit']}\nResets at: {r['reset_at']}"


def _tool_keys_list() -> str:
    result = _request("GET", "/api/keys")
    keys = result.get("keys", [])
    if not keys:
        return "No API keys found."
    lines = ["ID                                    Name        Key (masked)     Created"]
    lines.append("─" * 80)
    for k in keys:
        masked = k["key"][:10] + "..."
        lines.append(f"{k['id']:<36}  {k['name']:<10}  {masked:<15}  {k['created_at'][:16]}")
    return "\n".join(lines)


def _tool_keys_create(name: str = "default") -> str:
    result = _request("POST", "/api/keys", {"name": name})
    lines = [
        f"New key created: {name}",
        "",
        f"API key : {result['api_key']}",
        f"Key ID  : {result['key_id']}",
        "",
        "This is the only time the full key is shown.",
    ]
    return "\n".join(lines)


def _tool_keys_rename(key_id: str, name: str) -> str:
    result = _request("PATCH", f"/api/keys/{key_id}", {"name": name})
    return f"Key {result['id']} renamed to '{result['name']}'."


def _tool_keys_delete(key_id: str) -> str:
    _request("DELETE", f"/api/keys/{key_id}")
    return f"Key {key_id} has been revoked."


# ---------------------------------------------------------------------------
# MCP stdio protocol
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "signup",
        "description": (
            "Create an eyeroll account (or retrieve an existing one) using an email address. "
            "Returns the API key to use with all other tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Your email address."},
            },
            "required": ["email"],
        },
    },
    {
        "name": "watch_video",
        "description": (
            "Analyze a video URL or local file path using the eyeroll hosted API. "
            "Returns a structured markdown report coding agents can act on."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Video URL or local file path."},
                "context": {"type": "string", "description": "Optional context (issue body, what to fix, etc.)."},
                "max_frames": {"type": "integer", "description": "Max key frames to analyze. Default: 20.", "default": 20},
            },
            "required": ["source"],
        },
    },
    {
        "name": "check_usage",
        "description": "Check how many eyeroll analyses you have used today and when the limit resets.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "keys_list",
        "description": "List all API keys associated with your eyeroll account.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "keys_create",
        "description": "Create a new eyeroll API key with an optional label name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Label for this key (e.g. 'ci-bot', 'laptop').", "default": "default"},
            },
            "required": [],
        },
    },
    {
        "name": "keys_rename",
        "description": "Rename an existing API key. Use keys_list to find the key ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_id": {"type": "string", "description": "ID of the key to rename."},
                "name": {"type": "string", "description": "New name for the key."},
            },
            "required": ["key_id", "name"],
        },
    },
    {
        "name": "keys_delete",
        "description": (
            "Permanently revoke an API key. At least one key must remain. "
            "Use keys_list to find the key ID."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "key_id": {"type": "string", "description": "ID of the key to delete."},
            },
            "required": ["key_id"],
        },
    },
]


def _send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _handle(msg: dict) -> None:
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        _send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "eyeroll", "version": "0.2.0"},
            },
        })

    elif method == "tools/list":
        _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})

    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            if tool_name == "signup":
                text = _tool_signup(args["email"])
            elif tool_name == "watch_video":
                text = _tool_watch_video(
                    source=args["source"],
                    context=args.get("context"),
                    max_frames=args.get("max_frames", 20),
                )
            elif tool_name == "check_usage":
                text = _tool_check_usage()
            elif tool_name == "keys_list":
                text = _tool_keys_list()
            elif tool_name == "keys_create":
                text = _tool_keys_create(args.get("name", "default"))
            elif tool_name == "keys_rename":
                text = _tool_keys_rename(args["key_id"], args["name"])
            elif tool_name == "keys_delete":
                text = _tool_keys_delete(args["key_id"])
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text}]},
            })
        except Exception as exc:
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            })

    elif method == "notifications/initialized":
        pass

    else:
        if msg_id is not None:
            _send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            _handle(msg)
        except json.JSONDecodeError as exc:
            _send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}})


if __name__ == "__main__":
    main()
