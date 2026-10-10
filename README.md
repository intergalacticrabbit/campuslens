# CampusLens

CampusLens turns campus notice images into clear, editable information and useful follow-up tasks. Upload a notice, let **Gemma 4 (`gemma-4-26b-a4b-it`) through the Gemini API** extract its title, deadline, venue, eligibility, and actions, then review and save the result in a local dashboard.

## Features

- A calm, single-workspace Gradio dashboard with separate Overview, Analyze notice, and My tasks views.
- Image upload with structured notice analysis; missing details are left blank instead of guessed.
- Editable extracted fields, deadline/venue/eligibility display, and action cards.
- Persistent local JSON storage for notices and tasks.
- Task search by action, notice title, or venue; open/completed filters and completion tracking.
- Validation for malformed data, duplicate notices/actions, and invalid stored JSON.
- The local dashboard binds only to `127.0.0.1`.

## Requirements

- Python 3.10 or newer.
- A Gemini API key from [Google AI Studio](https://aistudio.google.com).

## Setup on Windows (PowerShell)

Run these commands from the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Paste your own key after `GEMINI_API_KEY=` in `.env`. Keep this file private; `.env` is excluded by `.gitignore`.

## Run the app

```powershell
python app.py
```

Open [http://127.0.0.1:7860](http://127.0.0.1:7860). Analyze a clear notice image, review and correct the extracted details, then save the notice and its action tasks. Use **My tasks** to search/filter tasks and mark one complete.

`app.py` calls `gemma_client.ask_with_image(...)`; `gemma_client.py` uses only `gemma-4-26b-a4b-it` through Google's Gemini API. Never add an API key to source code or a commit.

## Dashboard preview

![CampusLens dashboard](./campuslens-dashboard.png)

## Data and privacy

Notices and tasks are stored in `data/campus_data.json` on this computer. The file is created the first time a notice is saved and is ignored by Git. Avoid saving sensitive personal information. Notice images are sent to Google's Gemini API for analysis when you select **Analyze notice**.

## Tests

Tests do not make a Gemini API call:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

They cover JSON response parsing, missing/invalid data, duplicate handling, persistence, search, task completion, and UI callbacks with the API mocked.

## Team branches

| Member | Branch | Focus |
|---|---|---|
| 1 | `feature/gemma-ai` | Image extraction |
| 2 | `feature/ui` | Gradio interface |
| 3 | `feature/tasks` | Persistent tasks |
| 4 | `feature/tools` | Agent tools |
| 5 | `feature/testing-docs` | Tests and submission documentation |

This integrated frontend/backend work is on `feature/ui`. Coordinate shared files and schema changes before merging parallel contributions.

## License

This project is licensed under the MIT License; see [LICENSE](LICENSE).
