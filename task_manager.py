"""
CampusLens - Task & Notice Management Service
Core business logic, deduplication, search, deadline tracking, and agent adapters.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import re

from models import NoticeItem, TaskItem, validate_notice_payload, parse_and_validate_date
from storage import storage, StorageEngine


class TaskManager:
    """Central business logic manager for CampusLens."""

    def __init__(self, engine: Optional[StorageEngine] = None):
        self.storage = engine or storage

    # =========================================================================
    # 1. NOTICE INGESTION & DEDUPLICATION (Connecting with Member 1)
    # =========================================================================

    def is_duplicate_notice(self, title: str, deadline: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a notice with essentially the same title and deadline is already stored.
        Prevents duplicate entries when students rescan the same circular.
        """
        norm_title = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
        notices = self.storage.load_notices()

        for n in notices:
            stored_norm = re.sub(r"[^a-zA-Z0-9]", "", n.get("title", "").lower())
            same_title = (norm_title in stored_norm or stored_norm in norm_title) and len(norm_title) > 4
            same_deadline = (n.get("deadline") == deadline) if deadline else True

            if same_title and same_deadline:
                return True, n
        return False, None

    def ingest_extracted_notice(self, raw_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Receives extracted JSON dictionary from Member 1 (gemma-4-26b-a4b-it output).
        Validates, deduplicates, stores notice, and auto-generates associated tasks.
        
        Returns:
            (success: bool, message: str, saved_notice_dict: dict)
        """
        # Validate required fields
        is_valid, err_msg = validate_notice_payload(raw_data)
        if not is_valid:
            return False, f"Validation Failed: {err_msg}", {}

        # Instantiate Notice model
        notice = NoticeItem.from_dict(raw_data)

        # Duplicate check
        is_dup, existing = self.is_duplicate_notice(notice.title, notice.deadline)
        if is_dup and existing:
            return True, f"Notice already exists ('{existing.get('title')}'). Skipped duplicate creation.", existing

        # Persist notice
        notice_dict = notice.to_dict()
        self.storage.append_notice(notice_dict)

        # Auto-create tasks from extracted action items
        created_tasks = []
        if notice.action_items:
            for item in notice.action_items:
                if str(item).strip():
                    task = TaskItem(
                        notice_id=notice.id,
                        notice_title=notice.title,
                        title=str(item).strip(),
                        deadline=notice.deadline,
                        priority="High" if "submit" in str(item).lower() or "fee" in str(item).lower() else "Medium"
                    )
                    self.storage.append_task(task.to_dict())
                    created_tasks.append(task.to_dict())
        else:
            # If no explicit action items, create a default review task
            default_task = TaskItem(
                notice_id=notice.id,
                notice_title=notice.title,
                title=f"Review & act on notice: {notice.title}",
                deadline=notice.deadline,
                priority="Medium"
            )
            self.storage.append_task(default_task.to_dict())
            created_tasks.append(default_task.to_dict())

        return True, f"Successfully saved notice and generated {len(created_tasks)} actionable task(s).", notice_dict

    # =========================================================================
    # 2. TASK OPERATIONS & TRACKING (Connecting with Member 2 UI)
    # =========================================================================

    def get_all_tasks(self, filter_status: str = "all") -> List[Dict[str, Any]]:
        """
        Retrieve tasks with optional status filter: 'all', 'pending', or 'completed'.
        """
        tasks = self.storage.load_tasks()
        if filter_status == "pending":
            tasks = [t for t in tasks if not t.get("completed", False)]
        elif filter_status == "completed":
            tasks = [t for t in tasks if t.get("completed", False)]
        
        # Sort pending first, then by deadline
        def sort_key(t):
            deadline = t.get("deadline") or "9999-99-99"
            return (t.get("completed", False), deadline)

        tasks.sort(key=sort_key)
        return tasks

    def toggle_task(self, task_id: str) -> Tuple[bool, str]:
        """Toggle completion status of a task."""
        tasks = self.storage.load_tasks()
        found = False
        new_status = False

        for t in tasks:
            if t.get("id") == task_id:
                t["completed"] = not t.get("completed", False)
                t["completed_at"] = datetime.now().isoformat() if t["completed"] else None
                new_status = t["completed"]
                found = True
                break

        if found:
            self.storage.save_tasks(tasks)
            status_str = "completed" if new_status else "pending"
            return True, f"Task marked as {status_str}."
        return False, "Task ID not found."

    def add_task(
        self,
        title: str,
        deadline: Optional[str] = None,
        priority: str = "Medium",
        notice_id: Optional[str] = None,
        notice_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Manually add a task or add via agent tool."""
        parsed_deadline = parse_and_validate_date(deadline)
        task = TaskItem(
            notice_id=notice_id,
            notice_title=notice_title,
            title=title.strip(),
            deadline=parsed_deadline,
            priority=priority
        )
        task_dict = task.to_dict()
        self.storage.append_task(task_dict)
        return task_dict

    def delete_task(self, task_id: str) -> bool:
        """Remove a task."""
        tasks = self.storage.load_tasks()
        new_tasks = [t for t in tasks if t.get("id") != task_id]
        if len(new_tasks) != len(tasks):
            self.storage.save_tasks(new_tasks)
            return True
        return False

    # =========================================================================
    # 3. DEADLINE & UPCOMING EVENT QUERIES
    # =========================================================================

    def get_upcoming_deadlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return closest upcoming deadlines from pending tasks."""
        today = date.today().isoformat()
        pending = [t for t in self.storage.load_tasks() if not t.get("completed", False) and t.get("deadline")]
        
        # Valid future or today deadlines
        upcoming = [t for t in pending if t.get("deadline") and str(t.get("deadline")) >= today]
        upcoming.sort(key=lambda x: str(x.get("deadline")))
        return upcoming[:limit]

    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Return pending tasks whose deadlines have passed."""
        today = date.today().isoformat()
        pending = [t for t in self.storage.load_tasks() if not t.get("completed", False) and t.get("deadline")]
        return [t for t in pending if str(t.get("deadline")) < today]

    # =========================================================================
    # 4. NOTICE RETRIEVAL & SEARCH (Connecting with Member 4 Agent Tools)
    # =========================================================================

    def get_all_notices(self) -> List[Dict[str, Any]]:
        notices = self.storage.load_notices()
        # Sort newest first
        notices.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return notices

    def search_notices(self, query: str) -> List[Dict[str, Any]]:
        """Search notices across title, category, summary, and action items."""
        if not query or not query.strip():
            return self.get_all_notices()

        q = query.lower().strip()
        results = []
        for n in self.storage.load_notices():
            title = n.get("title", "").lower()
            cat = n.get("category", "").lower()
            summary = n.get("summary", "").lower()
            venue = str(n.get("venue", "")).lower()
            actions = " ".join(n.get("action_items", [])).lower()

            if q in title or q in cat or q in summary or q in venue or q in actions:
                results.append(n)
        return results

    # =========================================================================
    # 5. DASHBOARD KPI SUMMARY (For Member 2 UI Header / Stats)
    # =========================================================================

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Provides quick numbers for the UI dashboard counters."""
        notices = self.storage.load_notices()
        tasks = self.storage.load_tasks()

        pending_tasks = [t for t in tasks if not t.get("completed", False)]
        completed_tasks = [t for t in tasks if t.get("completed", False)]
        upcoming = self.get_upcoming_deadlines(limit=10)
        overdue = self.get_overdue_tasks()

        return {
            "total_notices": len(notices),
            "total_tasks": len(tasks),
            "pending_tasks": len(pending_tasks),
            "completed_tasks": len(completed_tasks),
            "upcoming_deadlines_count": len(upcoming),
            "overdue_count": len(overdue)
        }


# Global instance for app-wide imports
task_manager = TaskManager()
