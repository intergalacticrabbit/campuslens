import json

import app
import gemma_client
from task_manager import NoticeStore


def test_analyze_notice_uses_gemma_and_returns_editable_values(monkeypatch):
    assert gemma_client.MODEL == "gemma-4-26b-a4b-it"
    calls = []

    def fake_ask_with_image(image_path, prompt, system):
        calls.append((image_path, prompt, system))
        return json.dumps(
            {
                "title": "Open house",
                "deadline": None,
                "venue": "Main Hall",
                "eligibility": "First-year students",
                "actions": ["Register online"],
            }
        )

    monkeypatch.setattr(app.gemma_client, "ask_with_image", fake_ask_with_image)

    fields = app.analyze_notice("notice.png")

    assert fields[:5] == (
        "Open house",
        "",
        "Main Hall",
        "First-year students",
        "Register online",
    )
    assert "review" in fields[5].lower()
    assert calls[0][0] == "notice.png"
    assert "actions" in calls[0][1]
    assert calls[0][2] == app.SYSTEM_RULE


def test_analyze_without_image_returns_helpful_message(monkeypatch):
    monkeypatch.setattr(
        app.gemma_client,
        "ask_with_image",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected API call")),
    )

    result = app.analyze_notice(None)

    assert result[:5] == ("", "", "", "", "")
    assert "upload" in result[5].lower()


def test_save_and_complete_task_callbacks_update_dashboard(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "STORE", NoticeStore(tmp_path / "campus_data.json"))

    saved = app.save_notice(
        "Film night",
        "Thursday",
        "Student lounge",
        "Open to all",
        "Bring your student ID\nBring your student ID",
        "",
        "open",
    )

    assert "Saved" in saved[0]
    assert "Film night" in saved[2]
    assert "Bring your student ID" in saved[3]
    choices = saved[5]["choices"]
    assert len(choices) == 1

    refreshed = app.complete_task(choices[0][1], "", "open")

    assert "Task marked complete" in refreshed[5]
    assert "Completed" in app.refresh_dashboard("", "done")[3]
    assert "1" in refreshed[0]
