"""
CampusLens - Data Models & Validation Schema
Defines structured schemas for Notices and Tasks extracted via gemma-4-26b-a4b-it.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import re


def generate_id(prefix: str = "item") -> str:
    """Generate a clean, unique short ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def parse_and_validate_date(date_str: Optional[str]) -> Optional[str]:
    """
    Standardize dates to ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM if parseable.
    Gracefully retains clean text if date is relative (e.g., 'Coming Monday').
    """
    if not date_str or not date_str.strip():
        return None
    
    cleaned = date_str.strip()
    # Check common ISO formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return cleaned


@dataclass
class TaskItem:
    """Actionable student task derived from a notice or added manually."""
    id: str = field(default_factory=lambda: generate_id("task"))
    notice_id: Optional[str] = None
    notice_title: Optional[str] = None
    title: str = ""
    deadline: Optional[str] = None
    priority: str = "Medium"  # Low, Medium, High, Urgent
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskItem":
        # Filter only known fields
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        if "deadline" in filtered:
            filtered["deadline"] = parse_and_validate_date(filtered.get("deadline"))
        return cls(**filtered)


@dataclass
class NoticeItem:
    """Structured campus circular/notice extracted by gemma-4-26b-a4b-it."""
    id: str = field(default_factory=lambda: generate_id("notice"))
    title: str = ""
    category: str = "General"  # Academic, Examination, Hackathon, Hostel, Placement, Event, Sports
    issuer: str = "Campus Administration"
    issue_date: Optional[str] = None
    deadline: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    summary: str = ""
    action_items: List[str] = field(default_factory=list)
    raw_extracted_text: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_filename: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NoticeItem":
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        
        # Clean list of action items
        if isinstance(filtered.get("action_items"), str):
            filtered["action_items"] = [item.strip() for item in filtered["action_items"].split("\n") if item.strip()]
        elif not isinstance(filtered.get("action_items"), list):
            filtered["action_items"] = []

        if "deadline" in filtered:
            filtered["deadline"] = parse_and_validate_date(filtered.get("deadline"))
        if "issue_date" in filtered:
            filtered["issue_date"] = parse_and_validate_date(filtered.get("issue_date"))
            
        return cls(**filtered)


def validate_notice_payload(payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that the incoming extraction from Member 1's Gemma output has essential fields.
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a dictionary"
    
    title = payload.get("title")
    if not title or not str(title).strip():
        return False, "Notice title is required and cannot be empty"
    
    if len(str(title).strip()) < 3:
        return False, "Notice title is too short"
        
    return True, None
