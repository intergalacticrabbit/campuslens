"""
CampusLens - Fast Backend Verification Script
"""

from storage import StorageEngine
from task_manager import TaskManager
from models import validate_notice_payload, NoticeItem, TaskItem
import agent_tools
import os
import shutil

def run_all_tests():
    test_dir = os.path.join(os.path.dirname(__file__), "test_temp_data")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

    engine = StorageEngine(data_dir=test_dir)
    tm = TaskManager(engine=engine)

    print("1. Testing Schema Validation...")
    v1, _ = validate_notice_payload({})
    assert not v1, "Empty payload should be invalid"
    v2, _ = validate_notice_payload({"title": "Test Title"})
    assert v2, "Valid payload should pass"
    print("   [PASS] Schema validation")

    print("2. Testing Ingestion & Automatic Task Generation...")
    payload = {
        "title": "Semester Registration 2026",
        "deadline": "2026-10-20",
        "venue": "Academic Portal",
        "action_items": ["Pay fees online", "Select elective courses"]
    }
    ok, msg, saved = tm.ingest_extracted_notice(payload)
    assert ok, f"Failed ingestion: {msg}"
    notices = tm.get_all_notices()
    assert len(notices) == 1, "Notice count should be 1"
    tasks = tm.get_all_tasks()
    assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"
    print("   [PASS] Ingestion & Task generation")

    print("3. Testing Deduplication...")
    ok2, msg2, _ = tm.ingest_extracted_notice(payload)
    assert ok2, "Deduplication should succeed gracefully"
    assert "already exists" in msg2, "Should detect duplicate"
    assert len(tm.get_all_notices()) == 1, "Duplicate notice should not be added"
    assert len(tm.get_all_tasks()) == 2, "Duplicate tasks should not be added"
    print("   [PASS] Deduplication prevented duplicate entries")

    print("4. Testing Task Completion Toggle...")
    task_id = tasks[0]["id"]
    t_ok, t_msg = tm.toggle_task(task_id)
    assert t_ok, "Toggle failed"
    completed_tasks = tm.get_all_tasks(filter_status="completed")
    assert len(completed_tasks) == 1, "Should have 1 completed task"
    print("   [PASS] Task completion toggle")

    print("5. Testing Search...")
    search_res = tm.search_notices("elective")
    assert len(search_res) == 1, "Search should find notice by action item keyword"
    print("   [PASS] Search works across circular details")

    # Clean up
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

    print("\n==========================================")
    print("ALL BACKEND & STORAGE TESTS PASSED (5/5)!")
    print("==========================================")

if __name__ == "__main__":
    run_all_tests()
