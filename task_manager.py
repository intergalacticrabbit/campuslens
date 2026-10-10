"""Validated local JSON storage for CampusLens notices and action tasks."""

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "campus_data.json"
NOTICE_FIELDS = ("title", "deadline", "venue", "eligibility")
MAX_TEXT_LENGTH = 1000
MAX_ACTIONS = 20


class NoticeDataError(ValueError):
    """Raised when notice or persisted task data is missing or malformed."""


class DuplicateNoticeError(NoticeDataError):
    """Raised when a notice with the same identifying details is already saved."""


def _clean_text(value, field, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise NoticeDataError(f"{field.capitalize()} must be text.")
    value = value.strip()
    if not value and optional:
        return None
    if not value:
        raise NoticeDataError(f"{field.capitalize()} is required.")
    if len(value) > MAX_TEXT_LENGTH:
        raise NoticeDataError(f"{field.capitalize()} is too long (maximum {MAX_TEXT_LENGTH} characters).")
    return value


def _normalise(value):
    return re.sub(r"\s+", " ", value.casefold()).strip()


def parse_notice_response(response_text):
    """Validate and normalize the JSON response returned by Gemma."""
    if not isinstance(response_text, str) or not response_text.strip():
        raise NoticeDataError("Gemma returned an empty response. Please analyze the image again.")

    response = response_text.strip()
    if response.startswith("```"):
        response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response, flags=re.IGNORECASE).strip()
    try:
        payload = json.loads(response)
    except json.JSONDecodeError as error:
        raise NoticeDataError(
            "Gemma's response was not valid JSON. Please analyze the image again."
        ) from error
    if not isinstance(payload, dict):
        raise NoticeDataError("Gemma's response must be a JSON object.")

    notice = {
        field: _clean_text(payload.get(field), field, optional=True)
        for field in NOTICE_FIELDS
    }
    if not notice["title"]:
        raise NoticeDataError("The notice title is missing. Check the image and try again.")

    actions = payload.get("actions", [])
    if actions is None:
        actions = []
    if not isinstance(actions, list):
        raise NoticeDataError("Actions must be a list of text items.")
    if len(actions) > MAX_ACTIONS:
        raise NoticeDataError(f"A notice can contain at most {MAX_ACTIONS} actions.")

    clean_actions = []
    seen_actions = set()
    for action in actions:
        clean_action = _clean_text(action, "action", optional=True)
        if clean_action:
            key = _normalise(clean_action)
            if key not in seen_actions:
                clean_actions.append(clean_action)
                seen_actions.add(key)
    notice["actions"] = clean_actions
    return notice


class NoticeStore:
    """Read and atomically update the app's local JSON data file."""

    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self._lock = threading.RLock()

    def _read(self):
        if not self.path.exists():
            return {"version": 1, "notices": [], "tasks": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise NoticeDataError(f"Could not read saved campus data: {error}") from error
        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("notices"), list)
            or not isinstance(data.get("tasks"), list)
        ):
            raise NoticeDataError("Saved campus data has an unsupported or invalid format.")

        notice_ids = set()
        for notice in data["notices"]:
            if (
                not isinstance(notice, dict)
                or not isinstance(notice.get("id"), str)
                or not isinstance(notice.get("title"), str)
                or not notice["title"].strip()
                or not isinstance(notice.get("actions"), list)
            ):
                raise NoticeDataError("Saved campus data contains a malformed notice.")
            notice_ids.add(notice["id"])
        for task in data["tasks"]:
            if (
                not isinstance(task, dict)
                or not isinstance(task.get("id"), str)
                or not isinstance(task.get("notice_id"), str)
                or task["notice_id"] not in notice_ids
                or not isinstance(task.get("text"), str)
                or not task["text"].strip()
                or not isinstance(task.get("completed"), bool)
            ):
                raise NoticeDataError("Saved campus data contains a malformed task.")
        return data

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temp_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temp_path, self.path)
        except OSError as error:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise NoticeDataError(f"Could not save campus data: {error}") from error

    def save_notice(self, notice):
        """Save a notice and make one open task per distinct action."""
        if not isinstance(notice, dict):
            raise NoticeDataError("Notice data must be an object.")
        normalized = {
            field: _clean_text(notice.get(field), field, optional=True)
            for field in NOTICE_FIELDS
        }
        if not normalized["title"]:
            raise NoticeDataError("A notice title is required.")

        actions = notice.get("actions", [])
        if not isinstance(actions, list) or len(actions) > MAX_ACTIONS:
            raise NoticeDataError(f"Actions must be a list of at most {MAX_ACTIONS} items.")
        clean_actions = []
        seen_actions = set()
        for action in actions:
            clean_action = _clean_text(action, "action", optional=True)
            if clean_action and _normalise(clean_action) not in seen_actions:
                clean_actions.append(clean_action)
                seen_actions.add(_normalise(clean_action))
        normalized["actions"] = clean_actions

        with self._lock:
            data = self._read()
            identity = tuple(
                _normalise(normalized[field] or "")
                for field in ("title", "deadline", "venue")
            )
            for saved in data["notices"]:
                saved_identity = tuple(
                    _normalise(saved.get(field) or "")
                    for field in ("title", "deadline", "venue")
                )
                if identity == saved_identity:
                    raise DuplicateNoticeError("This notice is already saved.")

            notice_id = uuid.uuid4().hex
            created_at = datetime.now(timezone.utc).isoformat()
            saved_notice = {
                "id": notice_id,
                **normalized,
                "created_at": created_at,
            }
            data["notices"].append(saved_notice)
            for action in clean_actions:
                data["tasks"].append(
                    {
                        "id": uuid.uuid4().hex,
                        "notice_id": notice_id,
                        "text": action,
                        "completed": False,
                        "created_at": created_at,
                    }
                )
            self._write(data)
            return saved_notice

    def list_notices(self):
        with self._lock:
            return list(reversed(self._read()["notices"]))

    def list_tasks(self, query="", status="open"):
        """Search action text and related notice details with an optional status filter."""
        if status not in ("open", "done", "all"):
            raise ValueError("Task status must be 'open', 'done' or 'all'.")
        if query is None:
            query = ""
        if not isinstance(query, str):
            raise ValueError("Task search query must be text.")
        query_key = _normalise(query)
        with self._lock:
            data = self._read()
        notice_by_id = {notice["id"]: notice for notice in data["notices"]}
        tasks = []
        for task in data["tasks"]:
            if status == "open" and task["completed"]:
                continue
            if status == "done" and not task["completed"]:
                continue
            notice = notice_by_id.get(task["notice_id"], {})
            searchable = " ".join(
                str(value or "")
                for value in (task["text"], notice.get("title"), notice.get("venue"))
            )
            if query_key and query_key not in _normalise(searchable):
                continue
            tasks.append({**task, "notice": notice})
        return list(reversed(tasks))

    def complete_task(self, task_id):
        """Mark a task complete and return its updated record."""
        with self._lock:
            data = self._read()
            for task in data["tasks"]:
                if task["id"] == task_id:
                    task["completed"] = True
                    task["completed_at"] = datetime.now(timezone.utc).isoformat()
                    self._write(data)
                    return {**task}
        raise NoticeDataError("That task no longer exists. Refresh the task list and try again.")

    def summary(self):
        with self._lock:
            data = self._read()
        completed = sum(task["completed"] for task in data["tasks"])
        return {
            "notices": len(data["notices"]),
            "open_tasks": len(data["tasks"]) - completed,
            "completed_tasks": completed,
        }


# =============================================================================
# High-Level TaskManager Adapter (for harness/tools.py & agent integrations)
# =============================================================================

class TaskManager:
    """Synchronized adapter providing helper queries for agent tools and CLI."""

    def __init__(self, store: Optional[NoticeStore] = None, engine: Any = None):
        if store is not None:
            self.store = store
        elif engine is not None and hasattr(engine, "data_dir"):
            self.store = NoticeStore(path=Path(engine.data_dir) / "campus_data.json")
        else:
            self.store = NoticeStore()

    def ingest_extracted_notice(self, raw_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        try:
            payload = dict(raw_data)
            if "action_items" in payload and "actions" not in payload:
                payload["actions"] = payload["action_items"]
            saved = self.store.save_notice(payload)
            return True, f"Successfully saved notice with {len(saved.get('actions', []))} action(s).", saved
        except DuplicateNoticeError as e:
            return True, f"Notice already exists ('{raw_data.get('title')}'). Skipped duplicate creation.", {}
        except NoticeDataError as e:
            return False, str(e), {}

    def get_all_notices(self) -> List[Dict[str, Any]]:
        return self.store.list_notices()

    def get_all_tasks(self, filter_status: str = "all") -> List[Dict[str, Any]]:
        status = "all" if filter_status == "all" else ("open" if filter_status == "pending" else "done")
        tasks = self.store.list_tasks(status=status)
        for t in tasks:
            t["title"] = t.get("text", "")
            t["deadline"] = t.get("notice", {}).get("deadline")
        return tasks


    def toggle_task(self, task_id: str) -> Tuple[bool, str]:
        try:
            updated = self.store.complete_task(task_id)
            return True, f"Task marked as completed."
        except NoticeDataError as e:
            return False, str(e)

    def search_notices(self, query: str) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return self.store.list_notices()
        q = _normalise(query)
        matches = []
        for n in self.store.list_notices():
            searchable = " ".join([
                n.get("title", ""),
                n.get("venue") or "",
                n.get("eligibility") or "",
                " ".join(n.get("actions", []))
            ])
            if q in _normalise(searchable):
                matches.append(n)
        return matches

    def get_upcoming_deadlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        open_tasks = self.store.list_tasks(status="open")
        upcoming = []
        for t in open_tasks:
            notice = t.get("notice", {})
            deadline = notice.get("deadline")
            if deadline:
                upcoming.append({
                    "id": t["id"],
                    "title": t["text"],
                    "deadline": deadline,
                    "notice_title": notice.get("title"),
                    "priority": "High" if "fee" in t["text"].lower() or "submit" in t["text"].lower() else "Medium"
                })
        return upcoming[:limit]

    def find_notices_by_deadline(self, before_date: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Return notices with valid deadlines on or before *before_date*, sorted earliest first.

        Args:
            before_date: Cutoff date in YYYY-MM-DD format (inclusive).
            max_results: Maximum number of notices to return (1–20, default 5).

        Raises:
            ValueError: If *before_date* is not a valid YYYY-MM-DD string or
                        *max_results* is outside the 1–20 range.
        """
        if not before_date or not isinstance(before_date, str) or not before_date.strip():
            raise ValueError("before_date must be a non-empty YYYY-MM-DD string.")

        before_date = before_date.strip()
        try:
            cutoff = date.fromisoformat(before_date)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid date format '{before_date}'. Use YYYY-MM-DD.")

        if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 20:
            raise ValueError("max_results must be an integer from 1 to 20.")

        matches = []
        for n in self.store.list_notices():
            raw_deadline = n.get("deadline")
            if not raw_deadline or not isinstance(raw_deadline, str):
                continue
            try:
                dl = date.fromisoformat(raw_deadline)
            except (TypeError, ValueError):
                continue
            if dl <= cutoff:
                matches.append(n)

        matches.sort(key=lambda x: str(x.get("deadline", "")))
        return matches[:max_results]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        s = self.store.summary()
        return {
            "total_notices": s["notices"],
            "total_tasks": s["open_tasks"] + s["completed_tasks"],
            "pending_tasks": s["open_tasks"],
            "completed_tasks": s["completed_tasks"],
            "upcoming_deadlines_count": len(self.get_upcoming_deadlines(limit=10))
        }


# Global app-wide instance
task_manager = TaskManager()
