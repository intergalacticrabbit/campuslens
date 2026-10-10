"""
CampusLens - Agent Tool Adapter Functions
Pure Python functions ready to be used with the @tool pattern in harness/tools.py
for gemma-4-26b-a4b-it agent workflows.
"""

from typing import Optional
from task_manager import task_manager


def search_campus_notices(keyword: str) -> str:
    """
    Search previously uploaded and extracted campus notices, circulars, and announcements.
    Use this tool whenever the student asks questions about events, rules, timetables, venues,
    or deadlines mentioned in college notices.
    
    Args:
        keyword: Search query such as 'hackathon', 'exam', 'fees', 'mess rebate', or venue name.
        
    Returns:
        Formatted summary of matching notices with dates, eligibility, and action items.
    """
    results = task_manager.search_notices(keyword)
    if not results:
        return f"No campus notices found matching '{keyword}'."
    
    lines = [f"Found {len(results)} matching notice(s):"]
    for i, n in enumerate(results, start=1):
        lines.append(f"\n{i}. **{n.get('title')}** (Category: {n.get('category', 'General')})")
        if n.get('issuer'):
            lines.append(f"   - Issued By: {n.get('issuer')}")
        if n.get('deadline'):
            lines.append(f"   - Deadline: {n.get('deadline')}")
        if n.get('venue'):
            lines.append(f"   - Venue: {n.get('venue')}")
        if n.get('eligibility'):
            lines.append(f"   - Eligibility: {n.get('eligibility')}")
        if n.get('summary'):
            lines.append(f"   - Summary: {n.get('summary')}")
        if n.get('action_items'):
            lines.append(f"   - Required Actions: {', '.join(n.get('action_items'))}")
            
    return "\n".join(lines)


def get_pending_deadlines(limit: int = 5) -> str:
    """
    Get a list of the closest upcoming campus deadlines and tasks that need student action.
    
    Args:
        limit: Maximum number of deadlines to return (default 5).
        
    Returns:
        Chronological list of upcoming deadlines and action items.
    """
    deadlines = task_manager.get_upcoming_deadlines(limit=limit)
    if not deadlines:
        return "No upcoming pending deadlines found."
    
    lines = ["Upcoming Campus Deadlines:"]
    for i, t in enumerate(deadlines, start=1):
        notice_context = f" (from notice: {t.get('notice_title')})" if t.get('notice_title') else ""
        lines.append(
            f"{i}. [{t.get('priority', 'Medium')}] {t.get('title')} — Due: {t.get('deadline')}{notice_context}"
        )
    return "\n".join(lines)


def add_campus_task(title: str, deadline: str = "", priority: str = "Medium") -> str:
    """
    Create a new student task or reminder derived from a campus notice or student prompt.
    
    Args:
        title: What the student needs to do (e.g., 'Submit fee receipt to Academic Office').
        deadline: Date in YYYY-MM-DD format if known.
        priority: Priority level: 'High', 'Medium', or 'Low'.
        
    Returns:
        Confirmation message with task details.
    """
    task = task_manager.add_task(
        title=title,
        deadline=deadline if deadline.strip() else None,
        priority=priority
    )
    return f"Created task: '{task['title']}' (Priority: {task['priority']}, Due: {task.get('deadline') or 'No date'}). Task ID: {task['id']}"


def complete_campus_task(task_id: str) -> str:
    """
    Mark an existing campus task as completed.
    
    Args:
        task_id: The ID of the task to mark complete.
        
    Returns:
        Status message confirming completion.
    """
    success, msg = task_manager.toggle_task(task_id)
    return msg


def find_notices_by_deadline(before_date: str, max_results: int = 5) -> str:
    """
    Find campus notices with deadlines on or before a given date, sorted earliest first.
    Use this tool when a student asks about upcoming deadlines within a time window.

    Args:
        before_date: Cutoff date in YYYY-MM-DD format (inclusive).
        max_results: Maximum number of results from 1 to 20 (default 5).

    Returns:
        Formatted list of matching notices with their deadlines, venues, and action items.
    """
    results = task_manager.find_notices_by_deadline(before_date, max_results=max_results)
    if not results:
        return f"No campus notices found with deadlines on or before {before_date}."

    lines = [f"Found {len(results)} notice(s) with deadlines on or before {before_date}:"]
    for i, n in enumerate(results, start=1):
        lines.append(f"\n{i}. **{n.get('title')}** (Category: {n.get('category', 'General')})")
        if n.get('issuer'):
            lines.append(f"   - Issued By: {n.get('issuer')}")
        if n.get('deadline'):
            lines.append(f"   - Deadline: {n.get('deadline')}")
        if n.get('venue'):
            lines.append(f"   - Venue: {n.get('venue')}")
        if n.get('eligibility'):
            lines.append(f"   - Eligibility: {n.get('eligibility')}")
        if n.get('summary'):
            lines.append(f"   - Summary: {n.get('summary')}")
        if n.get('action_items'):
            lines.append(f"   - Required Actions: {', '.join(n.get('action_items'))}")
        if n.get('source_filename'):
            lines.append(f"   - Source: {n.get('source_filename')}")

    return "\n".join(lines)

