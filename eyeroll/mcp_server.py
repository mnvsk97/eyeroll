"""eyeroll MCP server — stdio transport.

The hosted eyeroll API is expected to be protected by platform auth such as
TrueFoundry endpoint authentication. This MCP server does not manage eyeroll
signup, API keys, or quotas.

Tools
-----
  watch_video    POST /api/watch — analyze a video and return an agent-ready report

Configuration:
  EYEROLL_API_URL  API base URL (default: https://api.eyeroll.dev)
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


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{_base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
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


def _tool_watch_video(
    source: str,
    context: str | None = None,
    max_frames: int = 20,
    repo_context: str | None = None,
) -> str:
    result = _request("POST", "/api/watch", {
        "source": source,
        "context": context,
        "max_frames": max_frames,
        "repo_context": repo_context,
    })

    lines = [
        f"Intent: {result.get('intent', 'unknown')}",
        f"Repo guess: {result.get('repo_guess', 'unknown')}",
        f"Handoff recommended: {result.get('handoff_recommended', False)}",
        f"Confidence: {result.get('confidence', 'unknown')}",
        "",
        result["report"],
    ]
    return "\n".join(lines)


TOOLS = [
    {
        "name": "watch_video",
        "description": (
            "Analyze a video URL using the hosted eyeroll API. Returns a structured "
            "markdown report with intent classification, repo guess, and an agent "
            "handoff section when code or docs work is recommended."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Video URL or source path the hosted API can access."},
                "context": {"type": "string", "description": "Optional context from the user, issue, Slack, or docs request."},
                "max_frames": {"type": "integer", "description": "Max key frames to analyze. Default: 20.", "default": 20},
                "repo_context": {"type": "string", "description": "Optional repo inventory or project context for repo inference."},
            },
            "required": ["source"],
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
                "serverInfo": {"name": "eyeroll", "version": "0.6.0"},
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
                    repo_context=args.get("repo_context"),
                )
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
