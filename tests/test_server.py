"""Tests for the hosted API surface."""

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
TestClient = fastapi_testclient.TestClient

from eyeroll.server.main import app


REPORT = """# eyeroll: checkout bug

## Video Analysis

### Metadata
```
intent: bug_report
category: bug
confidence: high
scope: in-context
repo_guess: web-app
repo_confidence: medium
severity: moderate
actionable: yes
handoff_recommended: yes
```

### Summary
Checkout fails.
"""


def test_watch_json_without_eyeroll_key(monkeypatch):
    async def fake_run_analysis(source, context, max_frames, repo_context=None):
        assert source == "https://example.com/demo.mp4"
        assert context == "checkout broken"
        assert max_frames == 12
        assert repo_context == "repo inventory"
        return REPORT

    monkeypatch.setattr("eyeroll.server.main._run_analysis", fake_run_analysis)

    client = TestClient(app)
    response = client.post(
        "/api/watch",
        json={
            "source": "https://example.com/demo.mp4",
            "context": "checkout broken",
            "max_frames": 12,
            "repo_context": "repo inventory",
        },
        headers={
            "x-tfy-user-email": "user@example.com",
            "x-tfy-workspace-id": "workspace-1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["report"] == REPORT
    assert body["intent"] == "bug_report"
    assert body["repo_guess"] == "web-app"
    assert body["handoff_recommended"] is True
    assert body["confidence"] == "high"


def test_watch_multipart_without_eyeroll_key(monkeypatch, tmp_path):
    async def fake_run_analysis(source, context, max_frames, repo_context=None):
        assert source.endswith("demo.mp4")
        assert context == "docs update"
        assert max_frames == 20
        assert repo_context == "docs repo"
        return REPORT

    monkeypatch.setattr("eyeroll.server.main._run_analysis", fake_run_analysis)

    client = TestClient(app)
    response = client.post(
        "/api/watch",
        data={"context": "docs update", "repo_context": "docs repo"},
        files={"file": ("demo.mp4", b"fake video", "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "bug_report"


def test_key_management_routes_are_not_exposed():
    client = TestClient(app)

    assert client.post("/signup", json={"email": "user@example.com"}).status_code == 404
    assert client.get("/api/keys").status_code == 404
    assert client.get("/api/usage").status_code == 404


def test_health():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
