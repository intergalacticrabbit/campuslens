"""
CampusLens - Backend Test & Verification Suite
Validates schema validation, deduplication, task generation, search, and agent tools.
Run: python test_backend.py
"""

import os
import shutil
import unittest
from storage import StorageEngine
from task_manager import TaskManager
from models import validate_notice_payload, NoticeItem, TaskItem
import agent_tools

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_data")

class TestCampusLensBackend(unittest.TestCase):

    def setUp(self):
        # Isolated test storage
        self.engine = StorageEngine(data_dir=TEST_DIR)
        self.engine.clear_all_data()
        self.tm = TaskManager(engine=self.engine)

    def tearDown(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR, ignore_errors=True)

    def test_schema_validation(self):
        """Ensure invalid or malformed extractions are rejected gracefully."""
        is_valid, err = validate_notice_payload({})
        self.assertFalse(is_valid)

        is_valid, err = validate_notice_payload({"title": ""})
        self.assertFalse(is_valid)

        is_valid, err = validate_notice_payload({"title": "Sports Meet 2026"})
        self.assertTrue(is_valid)

    def test_notice_ingestion_and_task_generation(self):
        """Ensure saving a notice auto-creates actionable tasks."""
        payload = {
            "title": "Hackathon Registration Final Reminder",
            "category": "Hackathon",
            "deadline": "2026-10-12",
            "venue": "Lab 1",
            "action_items": [
                "Form team of 4 members",
                "Submit team details on portal"
            ]
        }
        success, msg, saved = self.tm.ingest_extracted_notice(payload)
        self.assertTrue(success)
        self.assertIn("Successfully saved", msg)

        # Check saved notice
        notices = self.tm.get_all_notices()
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]["title"], payload["title"])

        # Check auto-generated tasks
        tasks = self.tm.get_all_tasks()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["deadline"], "2026-10-12")

    def test_deduplication(self):
        """Ensure scanning the same notice twice does not duplicate tasks."""
        payload = {
            "title": "Semester Fee Payment Notice",
            "deadline": "2026-11-01",
            "action_items": ["Pay fee online"]
        }
        success1, msg1, _ = self.tm.ingest_extracted_notice(payload)
        self.assertTrue(success1)

        # Ingest again
        success2, msg2, _ = self.tm.ingest_extracted_notice(payload)
        self.assertTrue(success2)
        self.assertIn("already exists", msg2)

        # Should still be 1 notice and 1 task
        self.assertEqual(len(self.tm.get_all_notices()), 1)
        self.assertEqual(len(self.tm.get_all_tasks()), 1)

    def test_task_toggle_and_deadlines(self):
        """Test task completion status and deadline filtering."""
        task = self.tm.add_task(title="Renew ID Card", deadline="2026-10-15")
        task_id = task["id"]

        # Initial pending
        pending = self.tm.get_all_tasks(filter_status="pending")
        self.assertEqual(len(pending), 1)

        # Toggle to completed
        ok, msg = self.tm.toggle_task(task_id)
        self.assertTrue(ok)
        self.assertIn("completed", msg)

        # Completed list check
        completed = self.tm.get_all_tasks(filter_status="completed")
        self.assertEqual(len(completed), 1)

    def test_search(self):
        """Test search across notices."""
        self.tm.ingest_extracted_notice({
            "title": "Inter-IIT Sports Trials",
            "venue": "Main Sports Complex",
            "summary": "Basketball and Badminton selections."
        })
        self.tm.ingest_extracted_notice({
            "title": "Coding Contest OpenLake",
            "venue": "Computer Centre",
            "summary": "Algorithm sprint."
        })

        results = self.tm.search_notices("sports")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Inter-IIT Sports Trials")

        results_venue = self.tm.search_notices("Computer")
        self.assertEqual(len(results_venue), 1)

if __name__ == "__main__":
    unittest.main()
