from typing import List, Optional
from pydantic import BaseModel, field_validator

FALLBACKS = {
    "title": "Untitled notice",
    "summary": "No summary was extracted from this notice.",
}


class Notice(BaseModel):
    title: str = FALLBACKS["title"]
    summary: str = FALLBACKS["summary"]
    deadlines: List[Deadline] = []
    event_date: Optional[str] = None
    time: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    actions: List[str] = []
    uncertainties: List[str] = []

    @field_validator("title", "summary", mode="before")
    @classmethod
    def fill_if_empty(cls, value, info):
        if value is None or not str(value).strip():
            return FALLBACKS[info.field_name]
        return value
