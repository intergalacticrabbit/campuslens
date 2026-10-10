from typing import List, Optional
from pydantic import BaseModel


class Deadline(BaseModel):
    date: Optional[str] = None
    what: str


class Notice(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    deadlines: List[Deadline] = []
    event_date: Optional[str] = None
    time: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    actions: List[str] = []
    uncertainties: List[str] = []