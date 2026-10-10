"""CampusLens: turn campus notice images into a searchable task dashboard."""

import html

import gradio as gr

import gemma_client
from task_manager import NoticeDataError, NoticeStore, parse_notice_response

TITLE = "CampusLens"
SYSTEM_RULE = (
    "You extract facts from campus notice images. Never guess missing details. "
    "Return only valid JSON with keys title, deadline, venue, eligibility, and actions. "
    "Use null when a detail is not stated. actions must be a JSON array of short, "
    "specific things a student needs to do."
)
STORE = NoticeStore()


def analyze_notice(image_path):
    """Ask Gemma to extract the notice details from an uploaded image."""
    if not image_path:
        return "", "", "", "", "", "Upload a notice image first."
    prompt = (
        "Read this campus notice and extract its information. Return exactly one JSON object "
        'with this shape: {"title": string, "deadline": string or null, "venue": string or null, '
        '"eligibility": string or null, "actions": [string, ...]}. '
        "Use null or an empty actions list for information that is not present. "
        "Do not infer or invent missing information."
    )
    try:
        response = gemma_client.ask_with_image(image_path, prompt, system=SYSTEM_RULE)
        notice = parse_notice_response(response)
    except NoticeDataError as error:
        return "", "", "", "", "", str(error)
    except Exception as error:
        return "", "", "", "", "", gemma_client.describe_error(error)
    return (
        notice["title"] or "",
        notice["deadline"] or "",
        notice["venue"] or "",
        notice["eligibility"] or "",
        "\n".join(notice["actions"]),
        "Notice analyzed. Review the extracted details, then save it.",
    )


def _escape(value):
    return html.escape(str(value or ""), quote=True)


def _render_notices(notices):
    if not notices:
        return (
            '<div class="empty-state"><span class="empty-icon">✦</span>'
            "<strong>Your notice board is ready</strong>"
            "<span>Analyze a campus notice to see deadlines and next steps here.</span></div>"
        )
    cards = []
    for notice in notices[:4]:
        details = [
            ("Deadline", notice.get("deadline")),
            ("Venue", notice.get("venue")),
            ("Eligibility", notice.get("eligibility")),
        ]
        detail_tags = "".join(
            f'<span class="notice-detail"><b>{label}</b> {_escape(value)}</span>'
            for label, value in details
            if value
        )
        action_count = len(notice.get("actions") or [])
        cards.append(
            '<article class="notice-card">'
            '<div class="notice-mark">N</div><div class="notice-content">'
            f'<div class="card-kicker">CAMPUS NOTICE</div>'
            f'<h3>{_escape(notice.get("title"))}</h3>'
            f'<div class="notice-details">{detail_tags}</div></div>'
            f'<span class="action-count">{action_count} actions</span></article>'
        )
    return '<div class="notice-stack">' + "".join(cards) + "</div>"


def _render_tasks(tasks):
    if not tasks:
        return (
            '<div class="empty-state"><span class="empty-icon">✓</span>'
            "<strong>All clear for now</strong>"
            "<span>Tasks from saved notices will show up here.</span></div>"
        )
    cards = []
    for task in tasks:
        notice = task.get("notice") or {}
        completed_class = " completed" if task.get("completed") else ""
        state = "Completed" if task.get("completed") else "To do"
        cards.append(
            f'<article class="task-card{completed_class}">'
            f'<span class="task-check">{ "✓" if task.get("completed") else "" }</span>'
            f'<div class="task-copy"><h3>{_escape(task.get("text"))}</h3>'
            f'<p>{_escape(notice.get("title") or "Campus notice")}</p></div>'
            f'<span class="task-state">{state}</span></article>'
        )
    return '<div class="task-stack">' + "".join(cards) + "</div>"


def refresh_dashboard(query="", status="open", feedback=""):
    """Render overview metrics, recent items, filtered tasks, and task choices."""
    summary = STORE.summary()
    stats = (
        '<div class="stats-grid">'
        '<div class="stat-card stat-mint"><span class="stat-icon">▤</span>'
        f'<span>Saved notices</span><strong>{summary["notices"]}</strong></div>'
        '<div class="stat-card stat-blue"><span class="stat-icon">↗</span>'
        f'<span>Open tasks</span><strong>{summary["open_tasks"]}</strong></div>'
        '<div class="stat-card stat-peach"><span class="stat-icon">✓</span>'
        f'<span>Completed</span><strong>{summary["completed_tasks"]}</strong></div>'
        "</div>"
    )
    choices = [
        (f'{task["text"]} — {task["notice"].get("title", "Campus notice")}', task["id"])
        for task in STORE.list_tasks(status="open")
    ]
    selected = choices[0][1] if choices else None
    recent_tasks = STORE.list_tasks(status="open")[:4]
    return (
        stats,
        _render_notices(STORE.list_notices()),
        _render_tasks(recent_tasks),
        _render_tasks(STORE.list_tasks(query=query, status=status)),
        gr.update(choices=choices, value=selected),
        feedback,
    )


def save_notice(title, deadline, venue, eligibility, actions, query, status):
    """Save reviewed notice fields and create a task for each distinct action."""
    notice = {
        "title": title,
        "deadline": deadline,
        "venue": venue,
        "eligibility": eligibility,
        "actions": actions.splitlines(),
    }
    try:
        saved = STORE.save_notice(notice)
        feedback = f'Saved "{saved["title"]}" and added its action items to your task list.'
    except NoticeDataError as error:
        feedback = str(error)
    return (feedback, *refresh_dashboard(query, status, feedback))


def complete_task(task_id, query, status):
    if not task_id:
        feedback = "Choose an open task first."
    else:
        try:
            STORE.complete_task(task_id)
        except NoticeDataError as error:
            feedback = str(error)
        else:
            feedback = "Task marked complete."
    return refresh_dashboard(query, status, feedback)


CSS = """
html, body, gradio-app { color-scheme: light; background: #eef5f2 !important; }
.gradio-container { max-width: 1480px !important; padding: 22px !important; }
main.fillable { width: 100% !important; max-width: none !important; }
.app-shell { width: 100% !important; max-width: none !important; gap: 18px !important; align-items: stretch; }
.sidebar {
    background: #18221f !important; border-radius: 18px; padding: 22px 16px !important;
    min-height: calc(100vh - 44px); color: #f7faf8;
}
.brand { padding: 4px 8px 26px; border-bottom: 1px solid #34413c; margin-bottom: 22px; }
.brand-mark {
    display: inline-flex; align-items: center; justify-content: center;
    width: 31px; height: 31px; border-radius: 10px; margin-right: 8px;
    color: #17382c; background: #62d6a2; font-size: 17px; font-weight: 800;
}
.brand-name { color: #fff; font-size: 18px; font-weight: 750; vertical-align: middle; }
.brand-caption { color: #a3b1ab; font-size: 11px; margin: 9px 0 0 40px; }
#campus-nav { background: transparent; border: 0; }
#campus-nav label {
    color: #c5d0cb; border: 0 !important; border-radius: 9px !important;
    padding: 10px 12px !important; margin: 3px 0 !important; transition: background .15s ease;
}
#campus-nav label:has(input:checked) { color: #123629; background: #43c991 !important; font-weight: 700; }
#campus-nav label:hover { background: #293631 !important; }
#campus-nav input { position: absolute; width: 1px; height: 1px; opacity: 0; }
.side-note {
    margin-top: 24px; padding: 12px; border: 1px solid #34413c; border-radius: 11px;
    color: #bdc9c3; font-size: 12px; line-height: 1.55;
}
.main-content { min-width: 0 !important; padding: 3px 4px 18px !important; }
.topbar { padding: 6px 4px 18px; border-bottom: 1px solid #dfe8e3; margin-bottom: 23px; }
.topbar-kicker { color: #73817b; font-size: 12px; text-transform: uppercase; letter-spacing: .1em; }
.topbar-title { color: #1c2a25; font-size: 24px; font-weight: 750; margin-top: 3px; }
.page-heading { margin: 0 0 5px !important; color: #1d2d27; }
.page-subtitle { color: #75847d; margin: 0 0 21px; font-size: 14px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 0 0 20px; }
.stat-card {
    min-height: 116px; padding: 17px 19px; border-radius: 14px; border: 1px solid #e3ebe6;
    display: grid; grid-template-columns: 34px 1fr; grid-template-rows: auto 1fr; column-gap: 12px;
    background: #fff;
}
.stat-mint { background: #ffddbd; }
.stat-blue { background: #d4e1f8; }
.stat-peach { background: #c8e2d8; }
.stat-icon {
    grid-row: 1 / 3; width: 32px; height: 32px; display: grid; place-items: center;
    background: #fff8; border-radius: 9px; color: #24463a; font-weight: 800;
}
.stat-card > span:nth-child(2) { color: #62716a; font-size: 12px; align-self: center; }
.stat-card strong { align-self: end; color: #202e28; font-size: 29px; line-height: 1.1; }
.content-panel {
    background: #fff; border: 1px solid #e2eae5; border-radius: 15px; padding: 19px 20px;
    box-shadow: 0 5px 18px #203b2c08;
}
.content-panel h3 { margin: 0 !important; color: #26352f; }
.panel-header { margin: 0 0 15px; }
.panel-caption { color: #87938d; font-size: 12px; margin-top: 4px; }
.notice-stack, .task-stack { display: grid; gap: 9px; }
.notice-card {
    display: flex; align-items: center; gap: 13px; border: 1px solid #edf1ee;
    border-radius: 12px; background: #fff; padding: 12px;
}
.notice-mark {
    flex: 0 0 38px; width: 38px; height: 38px; display: grid; place-items: center;
    border-radius: 10px; background: #e0f5eb; color: #269765; font-weight: 800;
}
.notice-content { min-width: 0; flex: 1; }
.card-kicker { color: #7b8982; font-size: 9px; font-weight: 750; letter-spacing: .09em; }
.notice-card h3 { margin: 2px 0 5px !important; color: #27352f; font-size: 14px; }
.notice-details { display: flex; flex-wrap: wrap; gap: 5px 12px; }
.notice-detail { color: #748179; font-size: 11px; }
.notice-detail b { color: #54635b; font-weight: 650; }
.action-count { white-space: nowrap; color: #32845f; background: #e5f6ed; border-radius: 20px; padding: 5px 9px; font-size: 10px; }
.task-card {
    display: flex; align-items: center; gap: 11px; border: 1px solid #edf1ee;
    border-radius: 11px; padding: 11px 12px; background: #fff;
}
.task-check {
    display: grid; place-items: center; width: 18px; height: 18px; flex: 0 0 18px;
    border: 1.5px solid #7a8b82; border-radius: 5px; color: #fff; font-size: 11px;
}
.task-copy { flex: 1; min-width: 0; }
.task-card h3 { margin: 0 0 3px !important; color: #26352f; font-size: 13px; }
.task-card p { margin: 0 !important; color: #8a9690; font-size: 11px; }
.task-card.completed .task-check { background: #35bd84; border-color: #35bd84; }
.task-card.completed h3 { color: #87938d; text-decoration: line-through; }
.task-state { color: #718078; font-size: 10px; white-space: nowrap; }
.empty-state {
    display: grid; justify-items: center; gap: 7px; padding: 35px 18px;
    border: 1px dashed #d9e3dd; border-radius: 12px; color: #718078 !important;
    background: #fbfdfc; text-align: center;
}
.empty-state span { color: #718078 !important; }
.empty-state strong { color: #46564e !important; font-size: 14px; }
.empty-icon { color: #39b982; font-size: 22px; }
.side-note { color: #bdc9c3 !important; }
.side-note b { color: #f1f8f4; }
.upload-panel, .extract-panel { height: 100%; }
.upload-hint { color: #7e8c84; font-size: 12px; line-height: 1.55; margin-top: 10px; }
.field-grid { gap: 10px !important; }
.status-message { color: #5e7067; font-size: 12px; }
.primary-button { background: #25b77b !important; border-color: #25b77b !important; }
.primary-button:hover { background: #1da36c !important; }
.quiet-button { border: 1px solid #dce6e0 !important; }
.page-content { gap: 16px !important; }
.task-toolbar { margin: 0 0 12px; }
.footer-note { color: #87948d; font-size: 11px; padding: 15px 4px 0; }
@media (max-width: 850px) {
    .gradio-container { padding: 12px !important; }
    .sidebar { min-height: auto; padding: 15px !important; }
    .brand { padding-bottom: 13px; margin-bottom: 10px; }
    .side-note { display: none; }
    .stats-grid { grid-template-columns: 1fr; }
}
"""


def select_page(page):
    """Switch between the dashboard, analyzer, and task management views."""
    return (
        gr.update(visible=page == "Overview"),
        gr.update(visible=page == "Analyze notice"),
        gr.update(visible=page == "My tasks"),
    )


def build_app():
    with gr.Blocks(title=TITLE) as demo:
        with gr.Row(elem_classes=["app-shell"]):
            with gr.Column(scale=2, min_width=190, elem_classes=["sidebar"]):
                gr.HTML(
                    '<div class="brand"><span class="brand-mark">C</span>'
                    '<span class="brand-name">CampusLens</span>'
                    '<div class="brand-caption">Your campus, in focus</div></div>'
                )
                page_nav = gr.Radio(
                    choices=["Overview", "Analyze notice", "My tasks"],
                    value="Overview",
                    label=None,
                    show_label=False,
                    container=False,
                    elem_id="campus-nav",
                )
                gr.HTML(
                    '<div class="side-note"><b>Notice to next step</b><br>'
                    "Keep campus deadlines and actions together in one calm workspace.</div>"
                )
            with gr.Column(scale=10, elem_classes=["main-content"]):
                gr.HTML(
                    '<div class="topbar"><div class="topbar-kicker">CAMPUS WORKSPACE</div>'
                    '<div class="topbar-title">A clearer view of what’s happening</div></div>'
                )
                with gr.Column(visible=True, elem_classes=["page-content"]) as overview_page:
                    gr.Markdown("## Overview", elem_classes=["page-heading"])
                    gr.Markdown(
                        "Your saved notices and the next steps that matter.",
                        elem_classes=["page-subtitle"],
                    )
                    metrics = gr.HTML()
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=7, min_width=260, elem_classes=["content-panel"]):
                            with gr.Row(elem_classes=["panel-header"]):
                                with gr.Column():
                                    gr.Markdown("### Recent notices")
                                    gr.HTML('<div class="panel-caption">The latest updates you saved</div>')
                            notice_cards = gr.HTML()
                        with gr.Column(scale=5, min_width=220, elem_classes=["content-panel"]):
                            with gr.Row(elem_classes=["panel-header"]):
                                with gr.Column():
                                    gr.Markdown("### Your next steps")
                                    gr.HTML('<div class="panel-caption">A few open actions to keep in view</div>')
                            overview_tasks = gr.HTML()
                    dashboard_message = gr.Textbox(
                        label="Update",
                        interactive=False,
                        lines=1,
                        elem_classes=["status-message"],
                    )

                with gr.Column(visible=False, elem_classes=["page-content"]) as analyze_page:
                    gr.Markdown("## Analyze a notice", elem_classes=["page-heading"])
                    gr.Markdown(
                        "Upload a clear photo. Review the extracted details before saving.",
                        elem_classes=["page-subtitle"],
                    )
                    with gr.Row(equal_height=False):
                        with gr.Column(scale=5, elem_classes=["content-panel", "upload-panel"]):
                            gr.Markdown("### 01 · Add your image")
                            image = gr.Image(
                                type="filepath",
                                sources=["upload"],
                                label="Notice image",
                                height=330,
                                show_label=False,
                            )
                            analyze_button = gr.Button(
                                "Analyze notice",
                                variant="primary",
                                elem_classes=["primary-button"],
                            )
                            gr.HTML(
                                '<div class="upload-hint">Use a sharp, well-lit image with all '
                                "notice text visible. Missing information is left blank.</div>"
                            )
                        with gr.Column(scale=7, elem_classes=["content-panel", "extract-panel"]):
                            gr.Markdown("### 02 · Review the details")
                            with gr.Row(elem_classes=["field-grid"]):
                                title = gr.Textbox(label="Title", placeholder="Notice title")
                                deadline = gr.Textbox(label="Deadline", placeholder="If stated")
                            with gr.Row(elem_classes=["field-grid"]):
                                venue = gr.Textbox(label="Venue", placeholder="If stated")
                                eligibility = gr.Textbox(label="Eligibility", placeholder="If stated")
                            actions = gr.Textbox(
                                label="Action items",
                                placeholder="One action per line",
                                lines=5,
                                info="Each action becomes a task when you save.",
                            )
                            save_button = gr.Button(
                                "Save notice and tasks",
                                variant="primary",
                                elem_classes=["primary-button"],
                            )
                            analysis_message = gr.Textbox(
                                label="Status",
                                interactive=False,
                                lines=2,
                                elem_classes=["status-message"],
                            )

                with gr.Column(visible=False, elem_classes=["page-content"]) as tasks_page:
                    gr.Markdown("## My tasks", elem_classes=["page-heading"])
                    gr.Markdown(
                        "Search, filter, and keep track of actions from your campus notices.",
                        elem_classes=["page-subtitle"],
                    )
                    with gr.Column(elem_classes=["content-panel"]):
                        with gr.Row(elem_classes=["task-toolbar"]):
                            task_search = gr.Textbox(
                                label="Search",
                                placeholder="Try an action, notice, or venue",
                                scale=5,
                            )
                            task_status = gr.Dropdown(
                                choices=[
                                    ("Open tasks", "open"),
                                    ("Completed", "done"),
                                    ("All tasks", "all"),
                                ],
                                value="open",
                                label="Show",
                                scale=2,
                            )
                        task_cards = gr.HTML()
                        with gr.Row():
                            task_picker = gr.Dropdown(
                                label="Choose an open task",
                                choices=[],
                                scale=5,
                            )
                            complete_button = gr.Button(
                                "Mark complete",
                                variant="primary",
                                scale=2,
                                elem_classes=["primary-button"],
                            )

                gr.HTML(
                    '<div class="footer-note">CampusLens · Powered by Gemma 4 · '
                    "Your saved notices stay on this device.</div>"
                )

        page_nav.change(
            select_page,
            inputs=[page_nav],
            outputs=[overview_page, analyze_page, tasks_page],
        )
        analyze_button.click(
            analyze_notice,
            inputs=[image],
            outputs=[title, deadline, venue, eligibility, actions, analysis_message],
            show_progress="full",
        )
        save_button.click(
            save_notice,
            inputs=[title, deadline, venue, eligibility, actions, task_search, task_status],
            outputs=[
                analysis_message,
                metrics,
                notice_cards,
                overview_tasks,
                task_cards,
                task_picker,
                dashboard_message,
            ],
            show_progress="minimal",
        )
        complete_button.click(
            complete_task,
            inputs=[task_picker, task_search, task_status],
            outputs=[
                metrics,
                notice_cards,
                overview_tasks,
                task_cards,
                task_picker,
                dashboard_message,
            ],
        )
        task_search.submit(
            refresh_dashboard,
            inputs=[task_search, task_status],
            outputs=[
                metrics,
                notice_cards,
                overview_tasks,
                task_cards,
                task_picker,
                dashboard_message,
            ],
        )
        task_status.change(
            refresh_dashboard,
            inputs=[task_search, task_status],
            outputs=[
                metrics,
                notice_cards,
                overview_tasks,
                task_cards,
                task_picker,
                dashboard_message,
            ],
        )
        demo.load(
            refresh_dashboard,
            inputs=[task_search, task_status],
            outputs=[
                metrics,
                notice_cards,
                overview_tasks,
                task_cards,
                task_picker,
                dashboard_message,
            ],
        )
    return demo


if __name__ == "__main__":
    print("Starting CampusLens at http://127.0.0.1:7860")
    build_app().launch(
        server_name="127.0.0.1",
        share=False,
        theme=gr.themes.Soft(primary_hue="emerald", neutral_hue="slate").set(
            body_background_fill="#eef5f2",
            body_background_fill_dark="#eef5f2",
            body_text_color="#20332a",
            body_text_color_dark="#20332a",
            body_text_color_subdued="#718078",
            body_text_color_subdued_dark="#718078",
            background_fill_primary="#ffffff",
            background_fill_primary_dark="#ffffff",
            background_fill_secondary="#f5f9f7",
            background_fill_secondary_dark="#f5f9f7",
            block_background_fill="#ffffff",
            block_background_fill_dark="#ffffff",
            block_label_text_color_dark="#53635b",
            input_background_fill_dark="#ffffff",
            input_border_color_dark="#dce6e0",
        ),
        css=CSS,
    )
