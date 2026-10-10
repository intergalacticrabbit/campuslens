"""FastAPI service for the CampusLens React frontend."""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import gemma_client
from task_manager import (
    NoticeDataError,
    NoticeStore,
    parse_notice_response,
    parse_email_response,
)

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

SYSTEM_RULE = (
    "You extract facts from campus notice images. Never guess missing details. "
    "Return only valid JSON with keys title, deadline, venue, eligibility, and actions. "
    "Use null when a detail is not stated. actions must be a JSON array of short, "
    "specific things a student needs to do."
)

EMAIL_SYSTEM_RULE = (
    "You are CampusLens, an intelligent email and announcement assistant for university students. "
    "Analyze the campus email or announcement text carefully. Extract the core information and assign an objective priority: "
    "- 'Urgent': Imminent deadline within 48 hours, examination/fee penalty, mandatory academic requirement, or critical emergency. "
    "- 'High': Important deadline within 7 days, course registration, scholarship, placement interview, or graded coursework. "
    "- 'Medium': General campus event, club announcement, guest lecture, hostel maintenance, or optional student opportunity. "
    "- 'Low': Routine newsletter, policy update without immediate action, or informational circular. "
    "Return strictly one valid JSON object with keys: "
    "subject (string), sender (string), priority ('Urgent'|'High'|'Medium'|'Low'), priority_reason (string explaining why), "
    "summary (concise 2-3 sentence overview), deadlines (array of strings), and action_items (array of short specific tasks for the student)."
)

STORE = NoticeStore()
app = FastAPI(title="CampusLens API", version="1.0.0")


class NoticeInput(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    deadline: str | None = Field(default=None, max_length=1000)
    venue: str | None = Field(default=None, max_length=1000)
    eligibility: str | None = Field(default=None, max_length=1000)
    actions: list[str] = Field(default_factory=list, max_length=20)


class EmailSummarizeInput(BaseModel):
    text: str = Field(min_length=5, max_length=20000)


class EmailInput(BaseModel):
    subject: str = Field(default="Campus Announcement", max_length=1000)
    sender: str = Field(default="Campus Office", max_length=1000)
    priority: str = Field(default="Medium", pattern="^(Urgent|High|Medium|Low)$")
    priority_reason: str = Field(default="", max_length=1000)
    summary: str = Field(default="", max_length=2000)
    deadlines: list[str] = Field(default_factory=list, max_length=10)
    actions: list[str] = Field(default_factory=list, max_length=20)



def _store_error(error):
    if isinstance(error, NoticeDataError):
        status = 409 if "already saved" in str(error).lower() else 400
        raise HTTPException(status_code=status, detail=str(error)) from error
    raise error


@app.get("/api/health")
def health():
    return {"status": "ok", "model": gemma_client.MODEL}


@app.get("/api/dashboard")
def dashboard():
    try:
        notices = STORE.list_notices()
        open_tasks = STORE.list_tasks(status="open")
        return {
            "summary": STORE.summary(),
            "notices": notices[:6],
            "upcoming_tasks": open_tasks[:5],
        }
    except NoticeDataError as error:
        _store_error(error)


@app.get("/api/notices")
def list_notices():
    try:
        return {"notices": STORE.list_notices()}
    except NoticeDataError as error:
        _store_error(error)


@app.post("/api/notices/analyze")
async def analyze_notice(image: UploadFile = File(...)):
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, WebP, or GIF image.")

    suffix = Path(image.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        suffix = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }[image.content_type]
    temporary_path = None
    try:
        contents = await image.read(MAX_IMAGE_BYTES + 1)
        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded image is empty.")
        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Images must be smaller than 12 MB.")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(contents)
        try:
            response = gemma_client.ask_with_image(
                str(temporary_path),
                "Read this campus notice and extract its information. Return exactly one JSON object "
                'with keys title (string), deadline (string or null), venue (string or null), '
                'eligibility (string or null), and actions (array of strings). Use null or an empty '
                "actions list when information is absent. Do not infer or invent missing details.",
                system=SYSTEM_RULE,
            )
            return {"notice": parse_notice_response(response)}
        except Exception as error:
            if isinstance(error, NoticeDataError):
                raise HTTPException(status_code=422, detail=str(error)) from error
            raise HTTPException(
                status_code=502,
                detail=gemma_client.describe_error(error),
            ) from error
    finally:
        await image.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@app.post("/api/notices", status_code=201)
def save_notice(notice: NoticeInput):
    try:
        saved = STORE.save_notice(notice.model_dump())
        return {"notice": saved}
    except NoticeDataError as error:
        _store_error(error)


@app.get("/api/tasks")
def list_tasks(
    query: str = Query(default="", max_length=200),
    status: str = Query(default="open", pattern="^(open|done|all)$"),
):
    try:
        return {"tasks": STORE.list_tasks(query=query, status=status)}
    except NoticeDataError as error:
        _store_error(error)


@app.patch("/api/tasks/{task_id}/complete")
def complete_task(task_id: str):
    try:
        return {"task": STORE.complete_task(task_id)}
    except NoticeDataError as error:
        _store_error(error)


@app.post("/api/emails/summarize")
def summarize_email(payload: EmailSummarizeInput):
    """Analyze and prioritize an email or announcement using Gemma 4."""
    try:
        response = gemma_client.ask(
            f"Analyze and prioritize this campus email:\n\n{payload.text}",
            system=EMAIL_SYSTEM_RULE,
        )
        return {"summary": parse_email_response(response)}
    except Exception as error:
        if isinstance(error, NoticeDataError):
            raise HTTPException(status_code=422, detail=str(error)) from error
        raise HTTPException(
            status_code=502,
            detail=gemma_client.describe_error(error),
        ) from error


@app.post("/api/emails", status_code=201)
def save_email(email: EmailInput):
    """Save a prioritized email summary to persistent campus data."""
    try:
        saved = STORE.save_email(email.model_dump())
        return {"email": saved}
    except NoticeDataError as error:
        _store_error(error)


@app.get("/api/emails")
def list_emails(priority: str = Query(default="all")):
    """List saved emails, sorted by priority (Urgent > High > Medium > Low)."""
    try:
        return {"emails": STORE.list_emails(priority_filter=priority)}
    except NoticeDataError as error:
        _store_error(error)



if FRONTEND_DIST.is_dir():
    assets_path = FRONTEND_DIST / "assets"
    if assets_path.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        requested = (FRONTEND_DIST / path).resolve()
        if path and requested.is_file() and requested.is_relative_to(FRONTEND_DIST.resolve()):
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")
