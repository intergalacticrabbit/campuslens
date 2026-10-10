"""
CampusLens - Persistent Storage Engine
Thread-safe, robust local JSON storage for notices and tasks.
"""

import json
import os
import threading
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NOTICES_FILE = os.path.join(DATA_DIR, "notices.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


class StorageEngine:
    """Manages persistent reading and writing of JSON data stores."""
    
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.notices_path = os.path.join(self.data_dir, "notices.json")
        self.tasks_path = os.path.join(self.data_dir, "tasks.json")
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory and files if they do not exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        for filepath in [self.notices_path, self.tasks_path]:
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)

    def _read_json(self, filepath: str) -> List[Dict[str, Any]]:
        with self._lock:
            if not os.path.exists(filepath):
                return []
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                return []

    def _write_json(self, filepath: str, data: List[Dict[str, Any]]) -> bool:
        with self._lock:
            try:
                # Write to temp file first to prevent corruption if interrupted
                temp_path = f"{filepath}.tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                # Atomic replace
                if os.path.exists(filepath):
                    os.replace(temp_path, filepath)
                else:
                    os.rename(temp_path, filepath)
                return True
            except OSError:
                return False

    # ---- Notices CRUD ----
    def load_notices(self) -> List[Dict[str, Any]]:
        return self._read_json(self.notices_path)

    def save_notices(self, notices: List[Dict[str, Any]]) -> bool:
        return self._write_json(self.notices_path, notices)

    def append_notice(self, notice: Dict[str, Any]) -> bool:
        notices = self.load_notices()
        notices.append(notice)
        return self.save_notices(notices)

    # ---- Tasks CRUD ----
    def load_tasks(self) -> List[Dict[str, Any]]:
        return self._read_json(self.tasks_path)

    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        return self._write_json(self.tasks_path, tasks)

    def append_task(self, task: Dict[str, Any]) -> bool:
        tasks = self.load_tasks()
        tasks.append(task)
        return self.save_tasks(tasks)

    def clear_all_data(self) -> None:
        """Utility for test resets."""
        with self._lock:
            self._write_json(self.notices_path, [])
            self._write_json(self.tasks_path, [])


# Global default instance
storage = StorageEngine()
