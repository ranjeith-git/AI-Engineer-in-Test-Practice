# Plan: Jira → LLM Test Case Generator (Streamlit, local-first)

## Goal
Build a runnable, two-page Python/Streamlit app under `Chapter03_Local_TC_Gen` that:
1. Lets the user type a request like *"create test cases for JIRA-123"`* and hits **Send**.
2. Parses the Jira ID, fetches the ticket via the **Jira REST API** (credentials from `.env`, which the user will share).
3. Loads a template file at runtime (single source of truth for test-case format — **never hardcoded in the app**), injects it into the LLM prompt with the ticket details.
4. Generates test cases via **Ollama (Gemma 3 1B, local, default)** with automatic **GROQ fallback** when Ollama is down/times out or the output structurally mismatches the template.
5. Exposes a **Settings page** that persists Jira URL / email / API token + GROQ token into the local `.env`.

## Decisions locked (confirmed with user)
- Template: reuse existing `templates/TC_template.md`; copy it to the runtime file `templates/test_cases_creator.md` (the name the spec expects) so the original stays untouched.
- Location: everything under `Chapter03_Local_TC_Gen`.
- Credentials: plain `.env` + `python-dotenv`, gitignored, with a committed `.env.example`.
- **`.env` already exists at `src/.env` (currently empty, where the user will paste credentials).** App loads/writes `src/.env` — NOT a new root `.env`. `.gitignore` must cover `src/.env` too.

## Project layout
```
Chapter03_Local_TC_Gen/
├── .gitignore                     # ignore src/.env, .env, app.log, __pycache__, .venv
├── .env.example                   # committed: keys + placeholder values, no real secrets
├── requirements.txt               # streamlit, requests, python-dotenv, pytest
├── README.md                      # setup, run, config reference
├── templates/
│   ├── TC_template.md             # existing source template (keep as-is)
│   └── test_cases_creator.md      # runtime copy — the app reads THIS at generation time
├── src/
│   ├── .env                       # ALREADY EXISTS (empty) — user pastes credentials here; NOT committed
│   ├── app.py                     # Streamlit entry — st.navigation between the 2 pages
│   ├── pages/
│   │   ├── chat_generate.py       # ChatGPT-style page: history, Send, streaming render, engine badge
│   │   └── settings.py            # masked form → writes .env via dotenv.set_key
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # loads src/.env → dataclass Settings; secrets redacted from any repr/log
│   │   ├── template_loader.py     # runtime read + light parse of template (headers/rules) + mtime note
│   │   ├── jira_client.py         # REST fetch + digest builder (summary/description/comments/AC)
│   │   ├── llm_client.py          # ollama_generate(), groq_generate(), route() with fallback
│   │   ├── output_validator.py    # checks output headers/IDs/priorities vs template; returns verdict
│   │   ├── pipeline.py            # orchestrates: jira → prompt build → route → validate → result
│   │   └── logger.py              # logging to app.log; guarantees no credential values are ever logged
│   └── prompts/
│       └── system_prompt.md       # role/instructions ONLY — contains NO column/format rules
└── tests/
    ├── test_template_loader.py    # fixture template files incl. missing/empty cases
    ├── test_output_validator.py   # valid row-set vs missing-column / bad-ID fixtures
    └── test_jira_id.py            # regex parse unit tests
```
Notes:
- `src/core/pipeline.py` is framework-agnostic; pages call it and render results — keeps logic testable without Streamlit.
- Chat state lives in `st.session_state["messages"]`; the Settings page writes `.env` and refreshes session state so changes apply to the *next* generation without restart.
- `config.py` resolves the `.env` path relative to the project root as `Chapter03_Local_TC_Gen/src/.env`.

## Module responsibilities

### config.py
- Loads `src/.env` with `dotenv.load_dotenv(dotenv_path=<project>/src/.env)`.
- `Settings` dataclass: `jira_url, jira_email, jira_api_token, groq_api_key, ollama_base_url, ollama_model, groq_model, template_path`.
- Defaults: `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=gemma3:1b`, `GROQ_MODEL=openai/gpt-oss-20b`, `TEMPLATE_FILE=templates/test_cases_creator.md` (all overridable in `src/.env`).
- `save_settings(...)` → `dotenv.set_key` writes back to `src/.env`; `__repr__`/log helper redacts token/email values.

### template_loader.py
- `load_template(path) -> TemplateFile` where `TemplateFile = {raw_text, expected_headers, ok, error}`.
- Reads the file fresh on every generation call — edits apply on the next run with no code change (satisfies the "template updated → picked up automatically" requirement).
- Missing / unreadable / empty file → `ok=False, error="..."` and the UI shows a clear message; generation stops. No fallback to a hardcoded default format.
- Light parse: finds the first markdown table, extracts the header row cell list (`| Test ID | Description | ... |`) and a rule summary used by the validator.

### jira_client.py
- `fetch_ticket(jira_url, email, token, issue_key)`:
  - `GET {jira_url}/rest/api/3/issue/{issue_key}?fields=summary,description,issuetype,status,priority,labels,components,creator,assignee,comment`
  - Auth header: `Authorization: Basic base64("{email}:{token}")`, `Accept: application/json`.
  - Raises typed errors (`JiraAuthError`, `JiraNotFoundError`, `JiraConnectionError`) mapped to friendly UI messages.
- `build_digest(issue) -> str`: markdown digest with Summary, Status, Type, Priority, Labels, Description, Comments. Acceptance criteria are extracted from the description when a clear `## Acceptance Criteria` section exists; otherwise the full description/comments travel to the LLM and anything missing reads "Not specified" (per template rule 7).

### llm_client.py
- `ollama_generate(settings, system, user) -> str` — `POST {base}/api/chat` (chat-templated, non-streaming, `temperature≈0.2`, configurable timeout ~180 s). Handles connection errors/timeouts as `EngineError`.
- `groq_generate(settings, system, user) -> str` — `POST https://api.groq.com/openai/v1/chat/completions`, `Bearer {groq_api_key}`, model from settings.
- `generate(...)` router (see pseudocode below): tries Ollama first, validates, falls back to GROQ on connectivity *or* structural mismatch, then returns `{engine, text, validated}`. Falls back again only once.
- NEVER logs request bodies or settings values (logger only records engine names, latency, and outcome).

### output_validator.py
- `validate(output_text, template_headers) -> ValidationResult {valid, reasons[]}`.
- Checks: at least one markdown table present; all expected headers present in the output header row; ≥1 data row; `Test ID` cells match `TC-\d+`; `Priority` values ∈ template's allowed set. Each failure adds a human-readable reason.
- Malformed output is **flagged, not silently displayed** — the UI shows the text with a warning banner plus reasons, and the router may have already retried GROQ.

### pipeline.py
- `run_generation(user_message, settings) -> PipelineResult {jira_key, digest, engine, text, validation}`.
- Steps: parse Jira ID → load template (fail fast with clear error if unusable) → fetch ticket → build system prompt from `prompts/system_prompt.md` (no format rules inside) + user message containing the template raw text and the ticket digest → `llm_client.generate(...)` → validate → return.

### pages
- **chat_generate.py**: `st.chat_input("e.g. create test cases for JIRA-123")` (Enter = Send — the ChatGPT interaction the mockup shows). Appends user message, runs pipeline with a spinner, renders assistant reply via `st.chat_message` + `st.markdown` (table renders natively). Under the reply: a small caption `Served by: Ollama gemma3:1b` / `GROQ` and a "Download .md" button when output is valid. Errors from the pipeline render as inline assistant error messages with the clear reason (missing template / Jira auth / engine unreachable).
- **settings.py**: masked `st.text_input(..., type="password")` fields for Jira email? no—email plain, token & GROQ key password-type; URL plain. "Save settings" button → `config.save_settings` → `st.toast`, no secrets echoed. Shows current Ollama reachability check (optional small "Test connection" button that only reports up/down).
- `src/app.py`: `st.navigation` with `st.Page` for the two pages, or `st.set_page_config` + manual routing on `st.session_state` — pick whichever the installed Streamlit version supports (documented in README).

### prompts/system_prompt.md
- Contains only: role (senior QA automation architect), mission, and the instruction that **the test-case structure/columns/numbering/rules come exclusively from the template content** embedded in the user message, plus "if information is missing write Not specified, never invent features". No column names or structural rules live here.

## Router pseudocode (llm_client.generate)
```
build messages (system + user)
try:
    text = ollama_generate(...)              # connectivity/timeout -> EngineError
    v = validate(text, template_headers)
    if v.valid: return {engine: "ollama", text}
    log("ollama output failed validation: reasons")
    raise EngineError("format mismatch")     # treated as fallback trigger
except EngineError:
    if no groq_api_key: return {engine:"ollama", text, validation:v}   # flagged, shown with warning
    text2 = groq_generate(...)               # EngineError -> raise friendly "both engines failed"
    v2 = validate(text2, template_headers)
    return {engine:"groq", text:text2, validation:v2}   # invalid groq output shown flagged, not silently
```

## Error handling & secret safety
- Every credential is read from `.env` at call time, never printed, never in `st.session_state` long-term except the masked password widgets' values, never written to logs. `logger.py` filters out values of known secret keys defensively.
- User-facing failures (Jira 401/404, Ollama down, template missing, both engines failed) surface as friendly inline messages; stack details go only to `app.log`.

## Verification
1. `pip install -r requirements.txt` (streamlit, requests, python-dotenv, pytest).
2. Populate `.env` from `.env.example` (user provides real Jira + GROQ values during implementation).
3. Unit tests: `python -m pytest tests/ -q` — covers template loader (valid/missing/empty), validator (valid, missing column, bad Test ID), Jira ID regex.
4. Manual, from `Chapter03_Local_TC_Gen`:
   - `streamlit run src/app.py` → Settings page: save dummy URL/email/token + GROQ key → confirm `.env` updated on disk and values not echoed.
   - Chat: `create test cases for JIRA-123` (or a real key) → markdown table rendered, engine caption visible, `app.log` shows engine + latency only.
   - Fallback: temporarily set `OLLAMA_BASE_URL=http://localhost:1` in `.env` → generation succeeds via GROQ, caption says GROQ.
   - Structural mismatch path: edit the template to add a bogus column → response is flagged with validation reasons (and GROQ retried when reachable).
   - Missing template path: rename `templates/test_cases_creator.md` → UI shows the clear error, no generation.
   - Edit `templates/test_cases_creator.md` column order → next generation reflects it without restart.

## Implementation order
1. `.gitignore` (ignore `src/.env`, `.env`, `app.log`, `__pycache__`, `.venv`), `.env.example`, `requirements.txt`.
2. `src/core/config.py`, `src/core/logger.py` (+ `__init__.py`).
3. `src/core/template_loader.py` + tests.
4. `src/core/output_validator.py` + tests.
5. `src/core/jira_client.py` (parse util + tests for ID regex).
6. `src/core/llm_client.py`, `src/core/pipeline.py`, `src/prompts/system_prompt.md`.
7. `src/pages/settings.py`, `src/pages/chat_generate.py`, `src/app.py`.
8. Copy `templates/TC_template.md` → `templates/test_cases_creator.md`.
9. `README.md` (setup, config table, template-location note, how settings are stored).
10. Create `src/.env` from the credentials the user shares (it already exists, empty); run tests + manual verification.

## Open note for implementation start
When the user pastes the `.env` contents, I will fill the existing `src/.env` with them, confirm `.gitignore` covers it, and run the app end-to-end with a real (or sample) Jira key the user provides.
