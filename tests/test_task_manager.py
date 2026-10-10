import json

import pytest

from task_manager import (
    DuplicateNoticeError,
    NoticeDataError,
    NoticeStore,
    parse_notice_response,
)


def test_parse_notice_response_accepts_markdown_json_and_deduplicates_actions():
    result = parse_notice_response(
        '```json\n{"title":"Tech Fest","deadline":"Friday","venue":null,'
        '"eligibility":"All students","actions":["Register"," Register "]}\n```'
    )

    assert result == {
        "title": "Tech Fest",
        "deadline": "Friday",
        "venue": None,
        "eligibility": "All students",
        "actions": ["Register"],
    }


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ("", "empty response"),
        ("not json", "not valid JSON"),
        ("[]", "JSON object"),
        ('{"deadline":"Friday","actions":[]}', "title is missing"),
        ('{"title":4,"actions":[]}', "Title must be text"),
        ('{"title":"Meeting","actions":"Attend"}', "Actions must be a list"),
    ],
)
def test_parse_notice_response_rejects_invalid_model_output(response, message):
    with pytest.raises(NoticeDataError, match=message):
        parse_notice_response(response)


def test_save_notice_persists_notice_and_unique_action_tasks(tmp_path):
    store = NoticeStore(tmp_path / "campus_data.json")
    saved = store.save_notice(
        {
            "title": "Hackathon",
            "deadline": "Friday 5 PM",
            "venue": "Innovation Lab",
            "eligibility": "All students",
            "actions": ["Register", " Register ", "Form a team"],
        }
    )

    tasks = store.list_tasks(status="open")
    assert saved["title"] == "Hackathon"
    assert {task["text"] for task in tasks} == {"Register", "Form a team"}
    assert all(task["notice"]["title"] == "Hackathon" for task in tasks)
    assert store.summary() == {"notices": 1, "open_tasks": 2, "completed_tasks": 0}
    assert json.loads((tmp_path / "campus_data.json").read_text())["version"] == 1


def test_duplicate_notice_is_rejected(tmp_path):
    store = NoticeStore(tmp_path / "campus_data.json")
    notice = {"title": "Workshop", "deadline": "Monday", "actions": ["Sign up"]}
    store.save_notice(notice)

    with pytest.raises(DuplicateNoticeError, match="already saved"):
        store.save_notice({**notice, "title": " WORKSHOP "})

    assert store.summary() == {"notices": 1, "open_tasks": 1, "completed_tasks": 0}


def test_search_and_task_completion(tmp_path):
    store = NoticeStore(tmp_path / "campus_data.json")
    store.save_notice(
        {
            "title": "Design workshop",
            "venue": "Design Lab",
            "actions": ["Bring a laptop", "Submit the form"],
        }
    )
    task = store.list_tasks(query="laptop", status="open")[0]

    completed = store.complete_task(task["id"])

    assert completed["completed"] is True
    assert [item["text"] for item in store.list_tasks(status="open")] == ["Submit the form"]
    assert len(store.list_tasks(query="design lab", status="done")) == 1
    assert store.summary() == {"notices": 1, "open_tasks": 1, "completed_tasks": 1}


def test_delete_completed_tasks_preserves_notices_and_open_tasks(tmp_path):
    store = NoticeStore(tmp_path / "campus_data.json")
    store.save_notice(
        {"title": "Project showcase", "actions": ["Register", "Bring a poster"]}
    )
    tasks = store.list_tasks(status="open")
    store.complete_task(tasks[0]["id"])

    assert store.delete_completed_tasks() == 1
    assert store.delete_completed_tasks() == 0
    assert len(store.list_notices()) == 1
    assert [task["text"] for task in store.list_tasks(status="all")] == ["Register"]
    assert store.summary() == {"notices": 1, "open_tasks": 1, "completed_tasks": 0}


def test_blank_search_query_can_be_none(tmp_path):
    store = NoticeStore(tmp_path / "campus_data.json")
    store.save_notice({"title": "Open day", "actions": ["Register"]})

    assert len(store.list_tasks(query=None, status="open")) == 1


def test_corrupt_saved_data_is_reported_without_being_overwritten(tmp_path):
    path = tmp_path / "campus_data.json"
    path.write_text("{broken", encoding="utf-8")
    store = NoticeStore(path)

    with pytest.raises(NoticeDataError, match="Could not read saved campus data"):
        store.list_notices()

    assert path.read_text(encoding="utf-8") == "{broken"
