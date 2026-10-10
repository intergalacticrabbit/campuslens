"""
CampusLens - Notice Extractor (Bridge for Member 1 & Gemma 4)
Uses gemma_client to read notice images and pipes structured data into TaskManager.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple

import gemma_client
from task_manager import task_manager

EXTRACT_PROMPT = """
You are CampusLens, an AI that analyzes college circulars, notice boards, and student announcements.
Analyze the provided notice image carefully.
Extract the structured information and respond ONLY with a valid JSON object (no markdown formatting, no code blocks):
{
  "title": "Clear concise notice title",
  "category": "Academic, Examination, Hackathon, Hostel, Placement, Event, or Sports",
  "issuer": "Issuing office or student body",
  "issue_date": "YYYY-MM-DD (or empty string if not mentioned)",
  "deadline": "YYYY-MM-DD (or empty string if not mentioned)",
  "venue": "Physical location or portal link",
  "eligibility": "Who this applies to",
  "summary": "2-sentence summary of the notice",
  "action_items": [
    "Action item 1 that student must do",
    "Action item 2 that student must do"
  ]
}
"""


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Parse JSON from model response, handling possible markdown fences."""
    cleaned = text.strip()
    # Strip markdown fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback to key-value regex extraction if json decode fails
        return {
            "title": "Extracted Campus Notice",
            "summary": cleaned[:300],
            "action_items": ["Review notice for details"]
        }


def analyze_and_ingest_notice_image(image_path: Path | str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Core end-to-end pipeline:
    1. Sends image to gemma-4-26b-a4b-it
    2. Parses JSON response
    3. Saves into persistent storage & auto-generates student tasks
    """
    path = Path(image_path)
    if not path.exists():
        return False, f"Image not found at {path}", {}

    try:
        # Query Gemma 4 vision model
        response_text = gemma_client.ask_with_image(path, EXTRACT_PROMPT)
        parsed_data = extract_json_from_response(response_text)
        parsed_data["source_filename"] = path.name

        # Hand off to TaskManager (Member 3 backend)
        success, msg, saved_notice = task_manager.ingest_extracted_notice(parsed_data)
        return success, msg, saved_notice
    except Exception as e:
        return False, f"Extraction failed: {gemma_client.describe_error(e)}", {}
