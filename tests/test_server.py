import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
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


def test_analysis_accepts_pdf_and_uses_gemma_pdf_helper(monkeypatch):
    observed = {}
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    pdf = BytesIO()
    writer.write(pdf)

    def fake_analyze(file_path, prompt, system):
        observed["path"] = Path(file_path)
        observed["contents"] = observed["path"].read_bytes()
        return json.dumps(
            {
                "title": "PDF notice",
                "deadline": None,
                "venue": None,
                "eligibility": None,
                "actions": [],
            }
        )

    monkeypatch.setattr(server.gemma_client, "ask_with_pdf", fake_analyze)
    response = TestClient(server.app).post(
        "/api/notices/analyze",
        files={"image": ("notice.pdf", pdf.getvalue(), "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["notice"]["title"] == "PDF notice"
    assert observed["contents"] == pdf.getvalue()
    assert not observed["path"].exists()


def test_analysis_rejects_malformed_pdf_before_model_call(monkeypatch):
    monkeypatch.setattr(
        server.gemma_client,
        "ask_with_pdf",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected model call")),
    )
    response = TestClient(server.app).post(
        "/api/notices/analyze",
        files={"image": ("notice.pdf", b"%PDF-invalid", "application/pdf")},
    )

    assert response.status_code == 422
    assert "could not be read" in response.json()["detail"]


def test_analysis_rejects_pdf_over_page_limit_before_model_call(monkeypatch):
    writer = PdfWriter()
    for _ in range(server.MAX_PDF_PAGES + 1):
        writer.add_blank_page(width=612, height=792)
    pdf = BytesIO()
    writer.write(pdf)
    monkeypatch.setattr(
        server.gemma_client,
        "ask_with_pdf",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected model call")),
    )
    response = TestClient(server.app).post(
        "/api/notices/analyze",
        files={"image": ("notice.pdf", pdf.getvalue(), "application/pdf")},
    )

    assert response.status_code == 413
    assert f"at most {server.MAX_PDF_PAGES} pages" in response.json()["detail"]


def test_text_analysis_extracts_and_validates_structured_notice(monkeypatch):
    observed = {}

    def fake_ask(prompt, system):
        observed["prompt"] = prompt
        observed["system"] = system
        return json.dumps(
            {
                "title": "Student research forum",
                "deadline": "May 4",
                "venue": "Library",
                "eligibility": "All students",
                "actions": ["Register online"],
            }
        )

    monkeypatch.setattr(server.gemma_client, "ask", fake_ask)
    response = TestClient(server.app).post(
        "/api/notices/analyze-text",
        json={"text": "Student research forum. Register by May 4 at the library."},
    )

    assert response.status_code == 200
    assert response.json()["notice"]["title"] == "Student research forum"
    assert response.json()["notice"]["actions"] == ["Register online"]
    assert "Student research forum" in observed["prompt"]
    assert observed["system"] == server.SYSTEM_RULE


def test_workspace_assistant_answers_with_saved_task_context(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    server.STORE.save_notice(
        {
            "title": "Research showcase",
            "deadline": "November 12, 2026",
            "venue": "Library Hall",
            "actions": ["Submit abstract", "Register online"],
        }
    )
    observed = {}

    def fake_ask(prompt, system):
        observed["prompt"] = prompt
        observed["system"] = system
        return "You have two open tasks for the Research showcase."

    monkeypatch.setattr(server.gemma_client, "ask", fake_ask)
    response = TestClient(server.app).post(
        "/api/assistant",
        json={
            "question": "Summarize my open tasks",
            "history": [{"role": "user", "content": "I need help planning."}],
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "You have two open tasks for the Research showcase."
    assert "Submit abstract" in observed["prompt"]
    assert "November 12, 2026" in observed["prompt"]
    assert "I need help planning." in observed["prompt"]
    assert "CampusLens Assistant" in observed["system"]


def test_workspace_assistant_rejects_blank_question(monkeypatch):
    monkeypatch.setattr(
        server.gemma_client,
        "ask",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected model call")),
    )
    response = TestClient(server.app).post(
        "/api/assistant",
        json={"question": "   "},
    )

    assert response.status_code == 422
    assert "Enter a question" in response.json()["detail"]


def test_workspace_assistant_reports_model_errors(monkeypatch):
    monkeypatch.setattr(
        server.gemma_client,
        "ask",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("Gemma is unavailable")),
    )
    monkeypatch.setattr(server.gemma_client, "describe_error", lambda error: str(error))

    response = TestClient(server.app).post(
        "/api/assistant",
        json={"question": "How should I prioritize?"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Gemma is unavailable"


def test_delete_completed_tasks_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    client = TestClient(server.app)
    client.post(
        "/api/notices",
        json={"title": "Career clinic", "actions": ["Book a slot", "Bring a CV"]},
    )
    task = client.get("/api/tasks").json()["tasks"][0]
    client.patch(f"/api/tasks/{task['id']}/complete")

    response = client.delete("/api/tasks/completed")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert len(client.get("/api/tasks", params={"status": "all"}).json()["tasks"]) == 1
    assert client.get("/api/dashboard").json()["summary"] == {
        "notices": 1,
        "open_tasks": 1,
        "completed_tasks": 0,
    }


def test_email_summarize_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "STORE", NoticeStore(tmp_path / "campus_data.json"))
    monkeypatch.setattr(
        server.gemma_client,
        "ask",
        lambda _prompt, system: json.dumps(
            {
                "subject": "Exam Hall Ticket Notice",
                "sender": "Academic Office",
                "priority": "High",
                "priority_reason": "Upcoming final examination requires mandatory verification",
                "summary": "Download and get verification signature before Friday.",
                "deadlines": ["Friday, Oct 16"],
                "action_items": ["Download admit card", "Get faculty signature"],
            }
        ),
    )

    client = TestClient(server.app)
    # Test summarize
    res = client.post("/api/emails/summarize", json={"text": "Exam hall tickets released..."})
    assert res.status_code == 200
    email_data = res.json()["email"]
    assert email_data["priority"] == "High"
    assert email_data["actions"] == ["Download admit card", "Get faculty signature"]

    # Test save email
    save_res = client.post("/api/emails", json=email_data)
    assert save_res.status_code == 201

    # Test list emails
    list_res = client.get("/api/emails")
    assert list_res.status_code == 200
    assert len(list_res.json()["emails"]) == 1
    assert list_res.json()["emails"][0]["subject"] == "Exam Hall Ticket Notice"
