import json
from pathlib import Path

from fastapi.testclient import TestClient

import server
from task_manager import NoticeStore


def test_dashboard_and_task_routes_use_the_notice_store(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    client = TestClient(server.app)

    created = client.post(
        "/api/notices",
        json={
            "title": "Design showcase",
            "deadline": "Friday",
            "venue": "Studio Hall",
            "eligibility": "All students",
            "actions": ["Register", "Bring your portfolio"],
        },
    )
    assert created.status_code == 201
    notice_id = created.json()["notice"]["id"]
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"] == {
        "notices": 1,
        "open_tasks": 2,
        "completed_tasks": 0,
    }
    assert dashboard.json()["notices"][0]["id"] == notice_id

    search = client.get("/api/tasks", params={"query": "portfolio", "status": "open"})
    assert search.status_code == 200
    task = search.json()["tasks"][0]
    assert task["text"] == "Bring your portfolio"
    completed = client.patch(f"/api/tasks/{task['id']}/complete")
    assert completed.status_code == 200
    assert completed.json()["task"]["completed"] is True


def test_duplicate_notice_returns_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    client = TestClient(server.app)
    notice = {"title": "Open lecture", "actions": []}

    assert client.post("/api/notices", json=notice).status_code == 201
    duplicate = client.post("/api/notices", json={**notice, "title": " open lecture "})

    assert duplicate.status_code == 409
    assert "already saved" in duplicate.json()["detail"]


def test_analysis_validates_upload_then_returns_structured_gemma_data(
    tmp_path, monkeypatch
):
    generated = {}

    def fake_analyze(image_path, prompt, system):
        generated["path"] = image_path
        generated["contents"] = open(image_path, "rb").read()
        generated["system"] = system
        return json.dumps(
            {
                "title": "Guest lecture",
                "deadline": "Wednesday",
                "venue": "Main hall",
                "eligibility": None,
                "actions": ["Register at the desk"],
            }
        )

    monkeypatch.setattr(server.gemma_client, "ask_with_image", fake_analyze)
    client = TestClient(server.app)

    response = client.post(
        "/api/notices/analyze",
        files={"image": ("notice.png", b"image bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["notice"]["title"] == "Guest lecture"
    assert response.json()["notice"]["actions"] == ["Register at the desk"]
    assert generated["contents"] == b"image bytes"
    assert generated["system"] == server.SYSTEM_RULE
    assert not Path(generated["path"]).exists()


def test_analysis_rejects_unapproved_upload_type(monkeypatch):
    monkeypatch.setattr(
        server.gemma_client,
        "ask_with_image",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected model call")),
    )
    client = TestClient(server.app)

    response = client.post(
        "/api/notices/analyze",
        files={"image": ("payload.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415


def test_email_summarize_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    monkeypatch.setattr(
        server.gemma_client,
        "ask",
        lambda _prompt, system=None: (
            '{"subject": "Fee Payment Deadline", "sender": "Accounts Office", '
            '"priority": "Urgent", "priority_reason": "Late fee applies tomorrow", '
            '"summary": "Pay tuition fee before 5 PM", "deadlines": ["Tomorrow 5 PM"], '
            '"action_items": ["Log in to portal", "Pay fee"]}'
        ),
    )
    client = TestClient(server.app)

    # Summarize email
    res = client.post("/api/emails/summarize", json={"text": "Please pay tuition fee before tomorrow."})
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["subject"] == "Fee Payment Deadline"
    assert summary["priority"] == "Urgent"

    # Save email
    saved = client.post("/api/emails", json=summary)
    assert saved.status_code == 201
    assert saved.json()["email"]["priority"] == "Urgent"

    # List emails
    listed = client.get("/api/emails")
    assert listed.status_code == 200
    assert len(listed.json()["emails"]) == 1

