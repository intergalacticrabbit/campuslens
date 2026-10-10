import json
import sys
from pathlib import Path

import gemma_client
from notice_schema import Notice

PDF_PROMPT = """Read this campus notice PDF. Reply with JSON only, no extra text, no markdown.
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
Rules: copy text exactly as written in the PDF. Never guess a date. If something is missing,
use null or an empty list and add a note to uncertainties. Read every page.
"""


def extract_notice_from_pdf(pdf_path: str) -> dict:
    """Read a PDF notice and return {"ok": True, "data": {...}} or {"ok": False, "error": ..., "detail": ..., "raw": ...}."""
    path = Path(pdf_path)
    if path.suffix.lower() != ".pdf":
        return {"ok": False, "error": "Not a PDF file", "detail": str(pdf_path), "raw": ""}
    if not path.exists():
        return {"ok": False, "error": "File not found", "detail": str(pdf_path), "raw": ""}

    raw = gemma_client.ask_with_image(path, PDF_PROMPT)
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return {"ok": True, "data": Notice.model_validate_json(cleaned).model_dump()}
    except ValueError as error:
        return {"ok": False, "error": "Model output did not match the schema", "detail": str(error), "raw": raw}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python read_pdf.py path/to/notice.pdf")
    print(json.dumps(extract_notice_from_pdf(sys.argv[1]), indent=2))