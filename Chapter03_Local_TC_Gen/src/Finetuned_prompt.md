Here's the updated RICE-POT prompt with explicit template-folder redirection built in:

---

**R — Role**
You are a senior Full-Stack Python Developer and QA Automation Architect with deep expertise in building local-first, LLM-integrated developer tools. You have strong experience with Streamlit (or equivalent lightweight Python frontend frameworks), Jira REST API integration, local LLM inference via Ollama, and cloud LLM fallback via GROQ. You follow production-grade coding standards, clean architecture, and secure credential handling.

**I — Instructions**
- Build a simple two-page Python web application (Streamlit, or the best-practice framework of your choice, as long as the stack is Python end-to-end).
- **Page 1 — Chat/Generate Screen:** A ChatGPT-style single-page interface where the user types a request (e.g., "create test cases for JIRA-123"), clicks a Send/Submit button, and sees the output rendered inline on the same page.
- **Page 2 — Settings Screen:** A form to save and persist Jira URL, Jira email ID, and Jira API token, plus the GROQ API token (as a fallback setting).
- On submit, parse the Jira ID from the user's message, fetch the corresponding Jira ticket details via the Jira REST API (using the saved URL/email/token).
- **Do not hardcode any test case structure, columns, or generation rules in the app or in the LLM prompt.** Instead, at generation time, the app must:
  1. Read `template/test cases creator.md` from the local template folder.
  2. Treat that file as the single source of truth for: column names/order, test case types to cover, serial numbering convention, structural rules, and any additional generation instructions written inside it.
  3. Dynamically inject the full contents of `test cases creator.md` into the LLM prompt/context alongside the fetched Jira ticket details, so the model generates output strictly conforming to what that file specifies.
- If `test cases creator.md` is missing, unreadable, or empty, the app must fail gracefully with a clear error message in the UI rather than falling back to an assumed/default format.
- If the template file is updated later, the app should pick up the new format automatically on the next run — no code changes required.
- **LLM logic:**
  - Primary: connect to the local Ollama instance running Gemma 3 (1B parameters) already active on `localhost`.
  - Fallback: if Ollama is unavailable, times out, or produces output that doesn't structurally match the template (e.g., wrong/missing columns), automatically retry via GROQ (groq.com) using the saved API token. Log which engine served each response.
- Keep the UI minimal, clean, and user-friendly — comparable to a polished consumer app, not a cluttered admin panel.
- Use secure, non-hardcoded credential storage (e.g., session state, `.env`, or an encrypted local config) for the Jira token and GROQ token — never print them in logs or UI.

**C — Context**
This is a local, single-user developer productivity tool. The end goal: a user pastes/types a Jira ticket ID, the app auto-fetches the ticket's summary/description/acceptance criteria from Jira, and generates a complete test case suite by combining that ticket data with the rules defined in `template/test cases creator.md`. The template file is the authoritative contract for format and coverage — the app is a pipeline (Jira data + template rules → LLM → structured output), not a source of formatting decisions itself.

**E — Example**
Follow the structure and conventions of the reference RICE-POT example (login page test case generation for app.vwo.com) as a model for how generated test cases should *read* in terms of clarity and rigor — but the actual columns, test case types, numbering, and any extra instructions must come exclusively from `template/test cases creator.md`, overriding this example wherever the two differ.

**P — Parameters**
- Language: Python only (frontend + backend logic).
- Framework: Streamlit preferred, or another Python framework if it better serves a ChatGPT-style single-page UX — justify the choice if not Streamlit.
- Must support two connection modes: Ollama (local, default) and GROQ (automatic fallback on failure or format mismatch).
- Must integrate real Jira REST API calls (not mocked), authenticated with email + API token.
- Must read and parse `template/test cases creator.md` at runtime (not build-time) so template edits take effect without redeployment.
- Output must be validated against the template's column/structure rules before being shown to the user; flag or reject malformed LLM output rather than silently displaying it.
- Code should be modular: separate modules for Jira client, LLM client (with Ollama/GROQ routing), template loader/parser, output validator, and UI pages.

**O — Output**
Deliver:
1. Complete, runnable Python project code (organized into files/modules), including the template-loading and output-validation logic.
2. Brief setup instructions (dependencies, how to run, expected location of `template/test cases creator.md`, how settings are stored).
No filler explanations beyond what's needed to run and understand the app structure.

**T — Tone**
Technical, precise, engineering-documentation style — no marketing language, no unnecessary elaboration.

---

One thing to confirm before this goes to a coding model: should the app treat `test cases creator.md` as plain text dropped into the LLM's context (simplest, most flexible), or do you want it actually *parsed* into a structured schema (e.g., regex/markdown-table extraction into a Python dict) so the output validator can programmatically check columns match? The first is simpler and more robust to template changes; the second gives stricter guarantees but breaks if the file's internal formatting shifts.