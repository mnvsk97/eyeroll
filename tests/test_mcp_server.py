"""Tests for the eyeroll MCP tool surface."""

from eyeroll import mcp_server


def test_mcp_exposes_only_watch_tool():
    tool_names = [tool["name"] for tool in mcp_server.TOOLS]

    assert tool_names == ["watch_video"]


def test_watch_tool_formats_structured_response(monkeypatch):
    def fake_request(method, path, body=None):
        assert method == "POST"
        assert path == "/api/watch"
        assert body["source"] == "https://example.com/demo.mp4"
        assert body["repo_context"] == "repo inventory"
        return {
            "intent": "documentation_update",
            "repo_guess": "docs",
            "handoff_recommended": True,
            "confidence": "medium",
            "report": "# Report",
        }

    monkeypatch.setattr(mcp_server, "_request", fake_request)

    text = mcp_server._tool_watch_video(
        "https://example.com/demo.mp4",
        context="update docs",
        repo_context="repo inventory",
    )

    assert "Intent: documentation_update" in text
    assert "Repo guess: docs" in text
    assert "Handoff recommended: True" in text
    assert "# Report" in text
