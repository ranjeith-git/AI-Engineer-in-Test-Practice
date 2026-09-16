---
name: resume-tailor
description: Tailor an existing resume to one specific job description and render it as an ATS-safe DOCX plus an audit XLSX workbook. Use when the user supplies a resume/CV and a job posting (pasted text, bullet list, file, or Excel) and asks for a tailored resume, an updated resume for a job, a resume version for this JD, or asks to "apply for this job with my resume".
argument-hint: "<job description text, or path to a JD file> [--master <path>] [--out <dir>]"
metadata:
  author: Ranjeith
  version: "1.0"
---

# Resume Tailor

Turn *"here is my old resume + this job description"* into a tailored resume as **DOCX + XLSX**.

The division of labour is strict and matters:

- **You (the agent) do all judgement and all writing.** Which bullets survive, how they are
  reworded, what is dropped, what the summary emphasises.
- **`scripts/build_resume.py` does all rendering.** It never invents content. It parses the
  resume spec you write and emits the DOCX + XLSX deterministically.

Never hand-roll a DOCX or XLSX with ad-hoc code, and never let the script "improve" wording.
If the output is wrong, the spec is wrong — fix the spec and re-render.

## Layout this skill assumes

```
<chapter>/                          <- RESUME_ROOT, default: the folder containing skills/
├── input/master_resume.md          <- master resume (source of truth, grows over time)
├── input/jd/<slug>.md              <- one job description per file
└── output/<date>_<company>_<role>/ <- generated resume.docx + resume_audit.xlsx
```

`RESUME_ROOT` defaults to the `skills/` folder's parent directory
(`${COMMANDCODE_SKILL_DIR}/../..`). Resolve all paths from there, not from the cwd.

Read [references/output-spec.md](references/output-spec.md) before you write a spec.
Read [references/tailoring.md](references/tailoring.md) before you rewrite any bullet.
Read [references/ats-rules.md](references/ats-rules.md) before you finalise.
Read [references/intake.md](references/intake.md) when the inputs are not already markdown.

## Step 1 — Locate the inputs

From the invocation arguments and the conversation, establish:

1. **The JD** — pasted text, a file path, an Excel row, or a bullet list. `$ARGUMENTS`
   carries these when invoked as `/resume-tailor`.
2. **The master resume** — prefer `input/master_resume.md`. If it does not exist, or still
   carries the `PLACEHOLDER` banner (unfilled template), ingest whatever the user supplied
   (docx / pdf / xlsx / md / txt) per [references/intake.md](references/intake.md) and **write
   `input/master_resume.md`** so every future application reuses it.

If neither a master nor a usable old resume is available, stop and ask for it — do not
reconstruct a resume from guesses or from the JD's wish list.

Tell the user which master you used and where you saved it. Then continue to Step 2 without
asking for further confirmation.

## Step 2 — Save the JD

Write the JD verbatim (plus its source URL/company if known) to
`input/jd/<company-or-role-slug>.md`. Never paraphrase a JD — the exact wording is the
keyword evidence you will be matching against later.

## Step 3 — Analyse the JD

Produce an explicit analysis before writing anything. For each requirement record:

| Field | Values |
|---|---|
| Requirement | the JD's own words, not a synonym |
| Priority | `must-have` (appears in requirements/responsibilities) / `nice-to-have` (preferred, bonus) |
| Category | skill, tool, domain, soft-skill, seniority, education |

Also capture: target title, seniority, domain, and the ATS platform if the JD or URL reveals
one (Workday, Taleo, Greenhouse, Lever, Naukri, SuccessFactors...).

Split compound bullets — "Python and Selenium with CI/CD experience" is **three** requirements
(Python, Selenium, CI/CD), not one.

## Step 4 — Map evidence from the master

For every requirement, find real evidence in the master resume and classify it:

- **Direct** — the master states it explicitly. Use the master's own figures.
- **Partial** — adjacent experience that plausibly transfers (Selenium → Playwright).
  Only usable if the user genuinely did the adjacent work; phrase it as what was done.
- **Gap** — nothing in the master supports it.

Record the mapping in the spec's `# JD Mapping` table. Compute coverage as
`(Direct + 0.5 × Partial) / must-have requirements`.

**Hard rule: never fabricate.** Do not invent employers, dates, degrees, certifications,
tools, metrics, or team sizes. Do not upgrade "familiar with" to "expert". Do not add a
skill to Core Skills that has no supporting evidence in the master. Gaps are reported to the
user in Step 8, never papered over in the resume.

## Step 5 — Tailor

Apply [references/tailoring.md](references/tailoring.md). The shape of the result:

1. **Headline** — mirrors the JD's title (only if the master supports that level).
2. **Summary** — 3–4 lines packed with the top must-have keywords, citing years of experience
   and the strongest quantified achievement. No first-person pronouns, no "seeking".
3. **Core Skills** — reordered so JD priorities come first; JD's own vocabulary used
   (if the JD says "test automation framework design", do not write "automation").
4. **Experience** — most recent first. For each role keep 3–6 bullets; front-load the ones
   matching must-haves. Rewrite every bullet as
   `Action verb + what + how (tool/method) + measurable outcome`. Preserve the truth of each
   fact — rewording is fine, re-aiming credit is not.
5. **Drop** — old/irrelevant roles compress to one line or are cut entirely; redundant
   bullets that hit no JD requirement are removed, not reworded.

Length: **2 pages max** (1 page if the master supports < 4 years or the JD is junior).
If you must cut, cut the weakest JD-matching content, never the contact block.

## Step 6 — Write the resume spec

Create `<out>/resume_spec.md` following
[references/output-spec.md](references/output-spec.md) exactly — the frontmatter keys and the
H1 section names are the renderer's contract. Use the required section names verbatim and
include all three analysis tables (`JD Mapping`, `Keywords`, `Gap Analysis`).

Start from [assets/master_resume.template.md](assets/master_resume.template.md) if you need
the skeleton.

## Step 7 — Render

Run this from anywhere; use the interpreter that has the dependencies:

```bash
python "${COMMANDCODE_SKILL_DIR}/scripts/build_resume.py" \
  "<out>/resume_spec.md" --out "<out>"
```

The script self-heals a missing `.venv`/dependency when a chapter venv exists. If it exits
with a dependency error instead, create the venv once and re-run:

```bash
python -m venv "<RESUME_ROOT>/.venv"
"<RESUME_ROOT>/.venv/Scripts/python.exe" -m pip install -r "<RESUME_ROOT>/requirements.txt"
```

Outputs: `resume.docx` (submit this) and `resume_audit.xlsx` (review this). Both are written
into `--out`, defaulting to `output/<date>_<company>_<role>/`.

## Step 8 — Verify, then report

**Relay the script's verification report.** It prints page estimate, quantified-bullet ratio,
keyword parity, unquantified/weak bullets and ATS violations. Read it back to the user; do not
claim success without it. Fix the spec and re-render when it flags a hard problem (missing
required section, invalid frontmatter).

Then write a short report:

- **Paths** — the two absolute artifact paths and the spec.
- **What changed vs the master** — reordered skills, rewritten bullets, dropped roles.
- **Coverage** — the score and the must-have keywords that are missing.
- **Gaps** — each gap, its severity, and the honest mitigation (e.g. "Selenium appears only
  in an internal tool — mention it in the cover letter rather than the resume").
- **Next actions** — anything the user should confirm as true, and what to add to the master.

Explicitly flag every claim the user should double-check (a number you reproduced from the
master, a Partial mapping phrased as adjacent experience).

## Keeping the master current

After rendering, if the conversation revealed facts not yet in `input/master_resume.md` (a
new project, a certification, a metric the user just stated), append them to the master so the
next application starts stronger. Only add what the user actually confirmed.

## Edge cases

| Situation | Do this |
|---|---|
| No master resume exists | Ingest what the user provides and create it (Step 1). Ask if nothing is provided. |
| JD is a thin list / job-board summary | Work with it; mark priorities from section headings; note the thin JD in the report. |
| Multiple JDs at once | Run Steps 2–8 once **per JD**, each into its own `output/` folder. Never merge. |
| User asks for several "versions" | Default is one tailored resume per JD. Offer extra variants (1-page, impact-heavy) only if asked, rendered from separate specs. |
| JD demands something the master lacks | Leave it out of the resume, list it as a Gap with mitigation. Never invent it. |
| Master has no metrics | Keep bullets truthful and achievement-shaped; tell the user to supply numbers. |
| Non-English JD | Write the resume in the JD's language only if the master supports it; otherwise ask. |
| Renderer errors on a section | The spec's heading is wrong — match the exact H1 names in `references/output-spec.md`. |

## Worked example

Input: an 8-year QA master resume + a "Senior SDET — Playwright, TypeScript, CI/CD, API
testing" JD.

1. JD saved to `input/jd/acme-senior-sdet.md`; six must-haves, three nice-to-haves.
2. Mapping: Playwright → *Partial* (2 years Cypress, directly transferable UI automation),
   TypeScript → *Direct*, CI/CD → *Direct* (Jenkins/GitHub Actions), API testing → *Direct*
   (Postman + RestAssured), Selenium → *Direct*, k6/load → *Gap*.
3. Summary leads with "8 years in test automation, TypeScript + Playwright/Cypress, CI/CD
   ownership" — every word traceable to the master.
4. Coverage `(5 + 0.5 × 1) / 6 = 92%`; k6 reported as a Gap with the mitigation "learning
   path — state load-testing exposure from JMeter only if true".
5. Rendered to `output/2026-09-16_acme_senior-sdet/` and the script's report relayed verbatim.
