"""
CampusLens - Backend Test & Verification Suite
"""

from run_tests import run_all_tests
import unittest
import os
import shutil
from task_manager import TaskManager

TEST_DIR = "test_data_deadline"

class TestFindNoticesByDeadline(unittest.TestCase):
    """Tests for TaskManager.find_notices_by_deadline (Member 4 contribution)."""

    def setUp(self):
        class DummyEngine:
            def __init__(self, data_dir):
                self.data_dir = data_dir
        self.engine = DummyEngine(data_dir=TEST_DIR)
        os.makedirs(TEST_DIR, exist_ok=True)
        # Clear data by just removing file if exists
        import contextlib
        with contextlib.suppress(FileNotFoundError):
            os.remove(os.path.join(TEST_DIR, "campus_data.json"))
        
        self.tm = TaskManager(engine=self.engine)
        
        # Seed three notices with different deadlines
        self.tm.ingest_extracted_notice({
            "title": "Early Deadline Notice",
            "category": "Academic",
            "deadline": "2026-10-12",
            "venue": "Room 101",
            "summary": "First to expire.",
            "action_items": ["Submit form"]
        })
        self.tm.ingest_extracted_notice({
            "title": "Mid Deadline Notice",
            "category": "Examination",
            "deadline": "2026-10-17",
            "venue": "Exam Hall",
            "summary": "Mid-range deadline.",
            "action_items": ["Print hall ticket"]
        })
        self.tm.ingest_extracted_notice({
            "title": "Late Deadline Notice",
            "category": "Event",
            "deadline": "2026-10-25",
            "venue": "Auditorium",
            "summary": "Latest deadline.",
            "action_items": ["Register online"]
        })
        # A notice without a deadline (should be skipped)
        self.tm.ingest_extracted_notice({
            "title": "No Deadline Notice",
            "category": "General",
            "summary": "This has no deadline."
        })

    def tearDown(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR, ignore_errors=True)

    def test_returns_notices_on_or_before_cutoff(self):
        """Cutoff 2026-10-17 should include the first two notices."""
        results = self.tm.find_notices_by_deadline("2026-10-17")
        self.assertEqual(len(results), 2)
        titles = [n["title"] for n in results]
        self.assertIn("Early Deadline Notice", titles)
        self.assertIn("Mid Deadline Notice", titles)

    def test_results_sorted_earliest_first(self):
        results = self.tm.find_notices_by_deadline("2026-12-31")
        deadlines = [n["deadline"] for n in results]
        self.assertEqual(deadlines, sorted(deadlines))

    def test_exact_deadline_match(self):
        """Cutoff equal to a notice's deadline should include it."""
        results = self.tm.find_notices_by_deadline("2026-10-12")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Early Deadline Notice")

    def test_no_match_for_early_cutoff(self):
        results = self.tm.find_notices_by_deadline("2020-01-01")
        self.assertEqual(len(results), 0)

    def test_far_future_includes_all_with_deadlines(self):
        """All three notices with deadlines should match; the one without should not."""
        results = self.tm.find_notices_by_deadline("2099-12-31")
        self.assertEqual(len(results), 3)

    def test_max_results_limits_output(self):
        results = self.tm.find_notices_by_deadline("2099-12-31", max_results=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Early Deadline Notice")

    def test_invalid_date_raises_error(self):
        with self.assertRaises(ValueError):
            self.tm.find_notices_by_deadline("not-a-date")

    def test_empty_date_raises_error(self):
        with self.assertRaises(ValueError):
            self.tm.find_notices_by_deadline("")

    def test_bool_max_results_raises_error(self):
        with self.assertRaises(ValueError):
            self.tm.find_notices_by_deadline("2026-12-31", max_results=True)

    def test_out_of_range_max_results_raises_error(self):
        with self.assertRaises(ValueError):
            self.tm.find_notices_by_deadline("2026-12-31", max_results=0)
        with self.assertRaises(ValueError):
            self.tm.find_notices_by_deadline("2026-12-31", max_results=21)

    def test_skips_notices_without_valid_deadline(self):
        """The 'No Deadline Notice' should never appear in results."""
        results = self.tm.find_notices_by_deadline("2099-12-31")
        titles = [n["title"] for n in results]
        self.assertNotIn("No Deadline Notice", titles)


if __name__ == "__main__":
    run_all_tests()
    print('\nRunning Member 4 Deadline Search Tests...')
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

