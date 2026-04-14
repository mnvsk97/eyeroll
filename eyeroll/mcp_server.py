"""eyeroll MCP server — stdio transport.

Exposes three tools for managing the eyeroll hosted API:
  - watch_video   POST /api/watch
  - check_usage   GET  /api/usage
  - rotate_key    POST /api/keys/rotate

Configuration (env vars):
  EYEROLL_API_KEY  Your eyeroll API key (required)
  EYEROLL_API_URL  API base URL (default: https://api.eyeroll.dev)

Run:
  python -m eyeroll.mcp_server
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.expanduser("~"), ".eyeroll", ".env"))
load_dotenv()


def _api_key() -> str:
    key = os.environ.get("EYEROLL_API_KEY", "")
    if not key:
        raise RuntimeError("EYEROLL_API_KEY is not set. Get a key at https://api.eyeroll.dev")
    return key


def _base_url() -> str:
    return os.environ.get("EYEROLL_API_URL", "https://api.eyeroll.dev").rstrip("/")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
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

def _tool_watch_video(source: str, context: str | None = None, max_frames: int = 20) -> str:
    result = _request("POST", "/api/watch", {
        "source": source,
        "context": context,
        "max_frames": max_frames,
    })
    return result["report"]


def _tool_check_usage() -> str:
    result = _request("GET", "/api/usage")
    return (
        f"Used today: {result['used_today']} / {result['limit']}\n"
        f"Resets at: {result['reset_at']}"
    )


def _tool_rotate_key() -> str:
    result = _request("POST", "/api/keys/rotate", {})
    return (
        f"New API key: {result['api_key']}\n\n"
        "Your old key is now invalid. Update EYEROLL_API_KEY in your environment."
    )


# ---------------------------------------------------------------------------
# MCP stdio protocol
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "watch_video",
        "description": (
            "Analyze a video URL or local file path using the eyeroll hosted API. "
            "Returns a structured markdown report that coding agents can act on."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Video URL (YouTube, Loom, etc.) or local file path.",
                },
                "context": {
                    "type": "string",
                    "description": "Optional context text (e.g. issue description, what to fix).",
                },
                "max_frames": {
                    "type": "integer",
                    "description": "Maximum key frames to analyze. Default: 20.",
                    "default": 20,
                },
            },
            "required": ["source"],
        },
    },
    {
        "name": "check_usage",
        "description": "Check how many eyeroll analyses you have used today and when the limit resets.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "rotate_key",
        "description": (
            "Rotate your EYEROLL_API_KEY. The current key is immediately invalidated "
            "and a new one is returned."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
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
                "serverInfo": {"name": "eyeroll", "version": "0.1.0"},
            },
        })

    elif method == "tools/list":
        _send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})

    elif method == "tools/call":
        params = msg.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            if tool_name == "watch_video":
                text = _tool_watch_video(
                    source=args["source"],
                    context=args.get("context"),
                    max_frames=args.get("max_frames", 20),
                )
            elif tool_name == "check_usage":
                text = _tool_check_usage()
            elif tool_name == "rotate_key":
                text = _tool_rotate_key()
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
        pass  # no response needed

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
