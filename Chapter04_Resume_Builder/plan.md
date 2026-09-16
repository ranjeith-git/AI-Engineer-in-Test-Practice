# Chapter 4 — Resume Builder: Implementation Plan

**Goal:** turn "here is my old resume + this job description" into a repeatable, one-command
workflow that produces a tailored resume as **DOCX + XLSX**, driven by a reusable agent skill.

**Decisions locked with the user**

| Decision | Choice |
|---|---|
| Output artifact | `.docx` (submit this) **and** `.xlsx` (audit/edit this) |
| Versions | **One master resume** (source of truth) + **one tailored resume per JD** |
| Skill location | Inside `Chapter04_Resume_Builder/` (a `skills/` folder in this chapter) |
| Input | Old resume in any format (docx/pdf/xlsx/md/txt) + JD as text list, file, or Excel |

---

## 1. Why the skill lives in `skills/` and how it still triggers

Command Code only auto-discovers skills from four roots:

1. `.commandcode/skills/` (project)  2. `.agents/skills/` (project)
3. `~/.commandcode/skills/` (user)   4. `~/.agents/skills/` (user)

...plus any folders listed in the `skills` array of a `settings.json`. Relative entries in that
array resolve against the **project root**, so adding:

```json
"skills": ["Chapter04_Resume_Builder/skills"]
```

to `.commandcode/settings.json` keeps the skill physically inside Chapter 4 — where the user
asked for it — while still making `/resume-tailor` discoverable from anywhere in the project.
(Verified: no user-level `settings.json` exists, so this project-level array shadows nothing.)

## 2. Architecture: markdown is the contract, Python is the renderer

This mirrors the Chapter 3 principle ("the template is the contract"): **the agent does all the
judgement and writing; the script does none of it.** The agent writes a *resume spec* markdown
file; the script deterministically renders it to DOCX + XLSX. Swapping the spec changes the
output with no code change.

```
master_resume.md ──┐
                   ├──> agent analyses/rewrites ──> resume_spec.md ──> build_resume.py ──> .docx + .xlsx
job_description ───┘
```

Why not have the script "think"? Because tailoring is a judgement task (which bullets to keep,
how to reword, what to leave out) and rendering is a mechanical task. Splitting them means the
XLSX audit tabs are always consistent with the DOCX, and the resume can be re-rendered at any
time from a saved spec.

## 3. Files to create

```
Chapter04_Resume_Builder/
├── plan.md                      # this file (deliverable)
├── README.md                    # how to run it, cold start
├── requirements.txt             # python-docx, openpyxl (pinned)
├── .gitignore                   # protects personal resume data
├── input/
│   ├── README.md                # where to drop the master resume + JDs
│   ├── master_resume.md         # normalised master (source of truth, grows over time)
│   └── jd/                      # one file per job description
├── output/                      # generated DOCX/XLSX per application (gitignored)
├── examples/                    # tiny synthetic run so output shape is verifiable
└── skills/resume-tailor/
    ├── SKILL.md                 # the 7-step playbook (< 500 lines)
    ├── references/
    │   ├── intake.md            # parsing any resume/JD format + master schema
    │   ├── tailoring.md         # bullet formulas, prioritisation, honesty rules
    │   ├── ats-rules.md         # ATS constraints + keyword parity rules
    │   └── output-spec.md       # exact resume-spec format + XLSX tab layout
    ├── assets/
    │   └── master_resume.template.md
    └── scripts/
        └── build_resume.py      # spec.md -> DOCX + XLSX + self-verification report
```

## 4. The playbook (what the skill tells the agent to do)

1. **Intake** — locate/parse the master resume and the JD into `input/master_resume.md` and a
   JD file. Never invent content: everything traceable back to the master.
2. **Analyse the JD** — split into must-have vs nice-to-have, extract keywords verbatim,
   detect seniority and domain, note the ATS platform if visible.
3. **Map evidence** — requirement → real evidence from the master, marked Direct / Partial /
   Gap. Compute a coverage score.
4. **Tailor** — rewrite the summary and bullets for this JD: JD vocabulary, XYZ formula,
   strongest evidence first, 2-page cap, no fabrication.
5. **Write the resume spec** — frontmatter + fixed H1 sections (the renderer's contract).
6. **Render** — `python scripts/build_resume.py <spec> --out output/<date>_<company>_<role>/`
   producing `resume.docx` and `resume_audit.xlsx`.
7. **Verify & report** — ATS checks, keyword parity, page estimate, then report exact paths,
   what changed, and the remaining gaps with suggested mitigations.

## 5. XLSX audit tabs (matches the agreed preview)

| Tab | Contents |
|---|---|
| `Master` | Full tailored resume, section by section — the editable working copy |
| `JD_Mapping` | Each JD requirement: priority, evidence, where it lands, Direct/Partial/Gap |
| `Bullets` | Every bullet: JD keywords hit, quantified?, which master item it came from |
| `Keywords` | Keyword, in JD / in master / in tailored, status |
| `Gap_Analysis` | Gap, severity, mitigation wording, cover-letter angle |

The `Bullets` tab is **derived** by the script from the experience section, so the spec isn't
duplicated and the audit can never drift from the resume.

## 6. DOCX rules (ATS-safe by construction)

Single column, no text boxes, no tables in the resume body, no graphics, standard section
headings, real Word bullet lists, dates as `MMM YYYY`, right-aligned dates via tab stops,
Calibri 10.5pt, 0.6" margins, max 2 pages.

## 7. Verification (runs on every invocation)

`build_resume.py` prints a report the agent must relay: estimated page count, quantified-bullet
ratio, keyword parity %, missing must-have keywords, weak/absent contact fields, and any
bullet that fails to start with an action verb. Exit code 2 on a hard contract violation
(missing required section), 0 otherwise with warnings.

## 8. Environment

`python` on this machine currently resolves to the **Chapter 3 venv**
(`Chapter03_Local_TC_Gen\.venv\Scripts\python.exe`), so Chapter 4 gets its **own** `.venv`
with `python-docx` + `openpyxl`. The script self-heals: if the libs are missing but a chapter
`.venv` exists, it re-executes itself with that interpreter, so `python scripts/build_resume.py`
works regardless of which environment is active.

## 9. Self-test before handover

Run the full pipeline on synthetic data (`examples/`): a fake master resume + a fake JD →
confirm both artifacts open, tabs and formatting are correct, coverage maths is right, and the
skill appears in `cmdc skills list` with no warning. Clean up nothing that isn't generated.
