# Jira → Test Case Generator

A local-first Python/Streamlit app (one app, three pages). You type a request
like `create test cases for JIRA-123`, the app fetches the ticket from Jira,
and an LLM generates a test-case suite whose **format is controlled entirely by
a local template file** — not by app code.

- **Page 1 — Chat / Generate:** ChatGPT-style. Ask for test cases for a Jira key; the
  markdown table renders inline, with a badge showing which engine served it.
- **Page 2 — Settings:** persist Jira URL / email / API token and the GROQ fallback key.
- **Page 3 — Error Log:** tail `app.log` in the browser (engine activity, Jira/Ollama/
  GROQ errors, validation flags) — the first stop when a launch or generation looks broken.

Double-click **`start_app.bat`** (Windows) or run **`./start_app.sh`** (macOS/Linux) to
launch the app and open your browser in one step.

## LLM routing

1. **Primary:** local Ollama (`gemma3:1b` by default) on `localhost:11434`.
2. **Fallback:** if Ollama is unreachable, times out, or returns output that fails
   structural validation against the template, the request is retried once via GROQ.
3. Which engine served each response is logged to `app.log` and shown under the result.

## Project layout

```
Chapter03_Local_TC_Gen/
├── .env.example                 # copy to src/.env and fill in real values
├── requirements.txt
├── start_app.bat                # Windows one-click launcher
├── start_app.sh                 # macOS/Linux one-click launcher
├── templates/
│   ├── TC_template.md           # source template (keep as reference)
│   └── test cases creator.md    # THE runtime template the app reads
├── src/
│   ├── .env                     # real credentials (gitignored) — app reads/writes this
│   ├── app.py                   # Streamlit entry point (3 pages)
│   ├── run_app.py               # launcher entry — used by start_app.bat/.sh
│   ├── pages/                   # chat_generate.py, settings.py, error_log.py
│   ├── core/                    # config, template_loader, jira_client,
│   │                            # llm_client, output_validator, pipeline, logger
│   └── prompts/system_prompt.md # role + rules only — NO format/column rules
└── tests/
```

## Setup

```bash
cd Chapter03_Local_TC_Gen
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

# 1) Copy the example and fill in your real values
copy .env.example src\.env        # Windows
# cp .env.example src/.env        # macOS / Linux

# 2) Ensure the runtime template exists
# templates/test cases creator.md is provided — edit it freely, changes apply
# on the next generation with no code change.
```

### Run — one click

- **Windows:** double-click `start_app.bat`
- **macOS/Linux:** `./start_app.sh`

or run directly:

```bash
streamlit run src/app.py          # or: .venv\Scripts\python src\run_app.py
```

The launchers use the project's `.venv` when present, verify `streamlit` is installed,
and print the last lines of `app.log` if startup fails — so a broken launch tells you
what broke instead of silently closing.

Open http://localhost:8501 → **Settings** → save your Jira URL, email, API token and
GROQ key. Then go to **Chat / Generate** and ask for test cases. If anything looks off,
open **Error Log** to see what happened.

## Configuration (src/.env)

| Key | Purpose |
|---|---|
| `JIRA_URL` | e.g. `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | your Jira account email |
| `JIRA_API_TOKEN` | Jira API token (not your password) |
| `GROQ_API_KEY` | GROQ key used when Ollama fails/mismatches |
| `OLLAMA_BASE_URL` | default `http://localhost:11434` |
| `OLLAMA_MODEL` | default `gemma3:1b` |
| `GROQ_MODEL` | default `openai/gpt-oss-20b` |
| `TEMPLATE_FILE` | default `templates/test cases creator.md` |

`src/.env` is gitignored and is never printed in the UI, logs, or chat history. The
Settings page writes back to the same file with `python-dotenv`.

## The template is the contract

`templates/test cases creator.md` is the single source of truth for the generated
format: column names/order, serial numbering, allowed Priority values, coverage rules,
and any extra instructions. At generation time the app:

1. reads the file fresh (edits apply on the next run — no code change);
2. injects its full contents into the LLM prompt alongside the Jira ticket digest
   (with the human-facing EXAMPLE ROW / `[PASTE REQUIREMENTS HERE]` placeholder
   stripped, so the model follows the real rules instead of echoing those);
3. validates the model output against the template's header row before showing it.

If the template is missing, unreadable, or empty the UI shows a clear error — the app
never falls back to a hardcoded format. If a generated table is missing a required
column, has malformed Test IDs, or uses a Priority outside the template's allowed set,
the output is flagged (and the GROQ retry is triggered when configured).

## Tests

```bash
python -m pytest tests/ -q
```

## Notes

- Jira Cloud REST (`/rest/api/3`) with Basic auth (`email:api_token`) — no code or
  token stored server-side.
- Jira issue text is converted from Atlassian Document Format to markdown for the LLM.
- If an "Acceptance Criteria" heading exists in the ticket, it is surfaced as its own
  section in the prompt.
- `app.log` records engine activity and errors only — credential values are redacted
  before anything is written, so the **Error Log** page is safe to open in the browser.
