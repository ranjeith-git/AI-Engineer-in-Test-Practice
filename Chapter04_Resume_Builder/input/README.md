# Input - where your inputs live

Two things go in here. Both are **gitignored**: your resume and the jobs you apply to never
leave this machine.

## 1. `master_resume.md` - your master resume (source of truth)

The complete, factual superset of your career. Every tailored resume is cut down from this file,
so keep it rich: every role, every achievement, every real number. Later runs *cut*, they never
invent.

You don't have to write it by hand. Hand the agent your existing resume in any format
(`.docx`, `.pdf`, `.xlsx`, `.md`, or pasted text) and ask it to normalise it into this file --
see `../skills/resume-tailor/references/intake.md` for how that conversion works.

If this file is still the unfilled placeholder, the skill treats it as *not yet provided* and
will ask for your real resume instead of using the blanks.

## 2. `jd/` - one job description per file

The skill writes these for you when you paste or point at a JD. Format:
`jd/<company>-<role>.md`, holding the posting **verbatim** plus its source URL and the ATS
platform if you know it.

Verbatim matters: the JD's exact wording is the keyword evidence used to check the finished
resume for ATS parity, and a paraphrase quietly removes matching keywords.

Applying to the same company twice? Use a dated slug so both survive:
`acme-senior-sdet-2026-09.md`.

## Where the results go

`../output/<date>_<company>_<role>/` -- `resume.docx` to submit, `resume_audit.xlsx` to review,
and `resume_spec.md` (the editable source) to re-render from.
