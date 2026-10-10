import json
import sys

import gemma_client
from notice_schema import Notice
"""     OUTPUT STRUCTURE 
{
  "ok": true,
  "data": {
    "title": "...",
    "summary": "...",
    "deadlines": [{"date": "...", "what": "..."}],
    "event_date": "...",
    "time": "...",
    "venue": "...",
    "eligibility": "...",
    "actions": ["..."],
    "uncertainties": ["..."]
  }
}



{
  "ok": false,
  "error": "Model output did not match the schema",
  "detail": "...",
  "raw": "..."
}

"""
PROMPT = """Read this campus notice. Reply with JSON only, no extra text, no markdown.
Use this exact shape:
{
  "title": string or null,
  "summary": string or null,
  "deadlines": [{"date": string or null, "what": string}],
  "event_date": string or null,
  "time": string or null,
  "venue": string or null,
  "eligibility": string or null,
  "actions": [string],
  "uncertainties": [string]
}
Rules: copy dates exactly as written. Never guess a date. If something is missing, use null or an empty list and add a note to uncertainties."""


def extract_notice(image_path: str) -> dict:
    raw = gemma_client.ask_with_image(image_path, PROMPT)
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return {"ok": True, "data": Notice.model_validate_json(cleaned).model_dump()}
    except ValueError as error:
        return {"ok": False, "error": "Model output did not match the schema", "detail": str(error), "raw": raw}
