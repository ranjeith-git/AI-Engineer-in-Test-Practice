# Memory

## Project

Practice repo for AI-assisted testing, organised one chapter per topic.

| Path | What it is |
|---|---|
| `Chapter01_LLM Basics/` | working notes on LLM fundamentals |
| `Chapter02_Prompt_Engg/` | prompt-engineering examples (RICEPOT) |
| `Chapter03_Local_TC_Gen/` | local Streamlit app: Jira ticket in, test cases out, format driven by `templates/test cases creator.md` |
| `Chapter04_Resume_Builder/` | `resume-tailor` skill: master resume + one JD -> tailored DOCX + audit XLSX |
| `scripts/push-review.py` | gated push helper (review, confirm, push) |

GitHub: `https://github.com/ranjeith-git/AI-Engineer-in-Test-Practice` -- **this repo is public.**

## Standing rules

### 1. Never push without explicit confirmation

The hard rule for this repo.

- Do not run `git push` until the user has explicitly said so **in the current conversation**
  for that specific change. "Sync my work" is a request to *start* the process, not consent to push.
- Before asking, show what would go up: branch, commits or files, and note that the repo is public.
- Ask a clear yes/no question and wait for the answer. If they don't answer, don't push.
- The user's own path is `scripts/push-review.py` (VS Code task **Git: Review & Push**), which
  requires typing `PUSH`. Never add a bypass flag to that gate.

### 2. Scope every commit, never blanket-commit

- Never `git add .` / `git add -A` followed by a bare `git commit`: the index often already holds
  unrelated staged work, and a bare commit sweeps all of it in.
- Prefer `git commit -F <messagefile> -- <path>` so the commit contains exactly the intended paths.
- One chapter, or one coherent change, per commit.

### 3. Secrets and personal data

- Public repo: never commit `.env`, tokens, keys or credentials. `.env.example` with placeholders only.
- `Chapter03_Local_TC_Gen/src/.env` is gitignored and must stay that way.
- Chapter 4 holds personal resume and JD data (`input/master_resume.md`, `input/jd/`, `output/`).
  Those are gitignored deliberately — never force-add them.
- Root `.gitignore` covers `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.venv/`.

## Commands

Tests:

- Chapter 3: `cd Chapter03_Local_TC_Gen && .venv\Scripts\python.exe -m pytest tests -q`
- Chapter 4: `cd Chapter04_Resume_Builder && .venv\Scripts\python.exe -m pytest tests -q`

Render a tailored resume (Chapter 4):

- `.venv\Scripts\python.exe skills\resume-tailor\scripts\build_resume.py <spec.md> --out <dir>`
  run from `Chapter04_Resume_Builder\`; add `--check-only` to validate without writing.

Pushing (always gated):

- `py -3 scripts/push-review.py --dry-run` to preview without changing anything
- `py -3 scripts/push-review.py` to review, confirm and push
