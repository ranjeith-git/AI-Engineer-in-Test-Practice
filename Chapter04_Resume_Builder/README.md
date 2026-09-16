# Chapter 4 - Resume Builder

A reusable agent skill that turns **your master resume + one job description** into a tailored
resume as **DOCX** (to submit) plus an **audit XLSX** (to review, edit and check for gaps).

The skill is at `skills/resume-tailor/`. Invoke it as `/resume-tailor`, or just ask in plain
language -- *"tailor my resume for this JD"* -- and it loads automatically.

- **One master resume** is the source of truth (`input/master_resume.md`). It grows over time.
- **One tailored resume per job description.** Never one compromise resume for every job.
- **Nothing is invented.** Every line traces back to the master; anything the JD wants that you
  don't have is reported as a gap instead of being quietly added.

## Layout

```
Chapter04_Resume_Builder/
├── plan.md                          # design + decisions (deliverable)
├── skills/resume-tailor/
│   ├── SKILL.md                     # the playbook the agent follows
│   ├── references/                  # intake, tailoring, ATS rules, spec format
│   ├── assets/master_resume.template.md
│   └── scripts/build_resume.py      # spec.md -> DOCX + XLSX + verification report
├── input/
│   ├── master_resume.md             # your master resume (gitignored - stays local)
│   └── jd/                          # one job description per file (gitignored)
├── output/<date>_<company>_<role>/  # generated resumes (gitignored)
├── examples/                        # synthetic fixture that proves the pipeline works
└── tests/                           # pytest suite for the renderer
```

## One-time setup

The skill self-heals: if the active Python lacks `python-docx`/`openpyxl`, it re-runs itself
under this chapter's `.venv`. Create that venv once:

**PowerShell**
```powershell
cd "C:\Users\Ranjeith\AI Testing\Chapter04_Resume_Builder"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**cmd**
```cmd
cd /d "C:\Users\Ranjeith\AI Testing\Chapter04_Resume_Builder"
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**macOS / Linux**
```bash
cd "Chapter04_Resume_Builder"
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Applying to a job

1. **Give the skill your inputs.** Either drop your current resume into
   `input/master_resume.md` (or hand the agent any `.docx`/`.pdf`/`.xlsx`/pasted text), and give
   it the JD -- pasted text, a bullet list, a file, or an Excel row.
2. **Invoke it:**
   ```
   /resume-tailor <paste the JD here>
   ```
3. **It will** normalise your master, analyse the JD, map your evidence to each requirement,
   rewrite summary/skills/bullets around that JD, and render:
   - `output/<date>_<company>_<role>/resume.docx` -- rename and submit this
   - `output/<date>_<company>_<role>/resume_audit.xlsx` -- review this
   - `output/<date>_<company>_<role>/resume_spec.md` -- the source, re-render any time
4. **Read the report it prints.** It lists coverage, keyword parity, page estimate, and every
   claim you should double-check. Fix and re-render rather than hand-editing the DOCX.

## What's in the audit workbook

| Tab | Use it to |
|---|---|
| `Master` | Read/edit the whole tailored resume row by row |
| `JD_Mapping` | See each JD requirement, your evidence, and Direct / Partial / Gap + coverage score |
| `Bullets` | Check every bullet for a number, an action verb, and which JD keywords it hits |
| `Keywords` | Confirm ATS keyword parity -- recomputed against your real master and resume |
| `Gap_Analysis` | See what the JD wants that you don't have, and how to handle it honestly |

The `JD_Mapping`, `Keywords` and `Gap_Analysis` tables are deliberately **absent from the DOCX**:
tables break ATS parsing, so they live in the workbook only.

## Running the renderer directly

```powershell
# validate a spec without writing anything
.venv\Scripts\python.exe skills\resume-tailor\scripts\build_resume.py output\<folder>\resume_spec.md --check-only

# render
.venv\Scripts\python.exe skills\resume-tailor\scripts\build_resume.py output\<folder>\resume_spec.md --out output\<folder>
```

Exit codes: `0` ok (warnings allowed), `2` spec/verification failure (fix the spec, don't ship),
`3` dependencies missing, `1` renderer fault.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

25 tests cover the spec contract, the parsing edge cases (soft-wrapped bullets, headings in the
wrong order, date formats), the coverage and keyword maths, the fabrication guard, and an
end-to-end render asserting the DOCX stays ATS-safe (no tables, no images, real bullet lists).

## Making the skill discoverable

Command Code auto-discovers skills from `.commandcode/skills/`, `.agents/skills/` and
`~/.commandcode/skills/`. This skill sits in `Chapter04_Resume_Builder/skills/` (outside those
roots), so `.commandcode/settings.json` at the repo root registers it:

```json
"skills": ["Chapter04_Resume_Builder/skills"]
```

Relative entries resolve against the project root. **Note:** `.commandcode/` is gitignored in
this repo, so that registration is machine-local -- on a fresh clone, re-add it, or load the
skill for one session with:

```powershell
cmd --skill "Chapter04_Resume_Builder/skills"
```

Check it is being seen:

```powershell
cmdc skills list
```

## Notes

- `input/`, `output/` and `examples/output/` are gitignored: your resume and the job
  descriptions you're applying to stay local and are never committed.
- `examples/` holds a fully synthetic candidate ("Alex Menon") used by the test suite. Delete it
  once you're comfortable -- nothing else depends on it except those tests.
- Adding new achievements to the master after a run makes every future application stronger;
  the skill appends what you confirm.
