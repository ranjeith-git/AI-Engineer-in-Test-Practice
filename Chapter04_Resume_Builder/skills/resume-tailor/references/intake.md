# Intake — turning whatever the user gives you into a master resume + a JD file

Two inputs are needed: the **master resume** and the **job description**. Neither has a fixed
format. Normalise both to markdown so every later run is deterministic.

## Master resume

Goal: `input/master_resume.md` — the durable source of truth. Every tailored resume is derived
from it, so it must be complete and factual, not tailored to any one JD.

### If the user supplies a file

| Format | How to read it |
|---|---|
| `.md` / `.txt` | `read_file` directly. |
| `.docx` | `read_file` (extracts to markdown), or `python -c "from docx import Document; ..."` in the chapter venv if structure matters. |
| `.pdf` | `read_file` (extracts the text layer). If "no text layer", ask for a DOCX/export — do not OCR-guess. |
| `.xlsx` | `read_file` (renders as tables) or `openpyxl` for cell-level detail. |
| Pasted in chat | Use it verbatim; ask for anything obviously truncated. |
| `.json` (LinkedIn / job-board export) | Map fields: `positions`, `education`, `skills`, `certifications`. |

### Normalising rules

1. **Preserve facts exactly** — employer names, titles, month/year ranges, locations, degrees.
   If a date is ambiguous (`2020–2023`), keep it as given and flag it for the user.
2. **Do not summarise away detail.** Intake is lossless: the master should be a *superset* of
   what will appear in any tailored resume. Later steps cut, never invent.
3. **Structure it** with the same H1 vocabulary the spec uses (`Contact`, `Summary`,
   `Core Skills`, `Experience`, `Education`, `Certifications`) — then Step 6 of the skill is a
   re-ordering/re-wording job rather than a rebuild.
4. **Collect metrics verbatim.** Numbers are the hardest thing to recover later. Keep every
   `%`, `$`, count, team size, and time saving exactly as stated.
5. **Mark uncertainty inline** as `<!-- confirm: ... -->` instead of guessing. Comments don't
   render and don't get copied into the tailored spec.

### If no master exists

Ask for it. One blunt question — "paste your current resume, or point me at the file" — beats
reconstructing one from the JD, which would be fabrication.

## Job description

Goal: `input/jd/<slug>.md`, written **verbatim**.

```markdown
# <Company> — <Role title>

Source: <URL or "pasted by user"> · Captured: <YYYY-MM-DD>

## Requirements
<the JD text, unedited>

## Responsibilities
<the JD text, unedited>

## Notes
- ATS: <Workday / Greenhouse / Lever / Taleo / Naukri / unknown>
- Recruiter email or referral, if visible
```

Rules:

- **Never paraphrase the JD.** The exact strings are the keyword evidence for
  [tailoring.md](tailoring.md) and the parity check in the renderer.
- If the user pastes a bullet list ("must know Playwright, TS, CI/CD"), keep it as-is under
  `## Requirements` — a thin JD is still a JD. Note in the report that it was thin, because
  coverage numbers on a 5-line JD are less meaningful.
- If a job-board summary is all that exists, record it and say so; don't inflate it.
- One file per JD. Re-applying to the same company later gets a new file with the date in the
  slug (`acme-senior-sdet-2026-09.md`).

## Multiple JDs

Process them one at a time through the whole workflow, each with its own
`output/<date>_<company>_<role>/`. Never blend two JDs into one resume — the keyword parity
check becomes meaningless and the user cannot tell which version they sent where.
