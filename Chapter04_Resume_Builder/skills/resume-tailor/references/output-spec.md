# Output spec — the resume spec format (the renderer's contract)

`build_resume.py` parses this file and writes `resume.docx` + `resume_audit.xlsx`. The
frontmatter keys and H1 section names below are **exact** — the parser matches them
case-insensitively but will not invent sections. Write the spec to
`output/<date>_<company>_<role>/resume_spec.md`.

## Frontmatter

```yaml
---
candidate: Ranjeith K
target_role: Senior SDET
company: Acme Corp
date: 2026-09-16
version: v1
master_source: input/master_resume.md
coverage_pct: 92
years_experience: 8
---
```

| Key | Required | Notes |
|---|---|---|
| `candidate` | **yes** | Full name as it should appear on the resume |
| `target_role` | **yes** | The JD's title; used when `# Contact` has no title line |
| `company` | no | Rendered in the verification report only |
| `date` | no | YYYY-MM-DD; use the render date |
| `version` | no | `v1`, `v2` … for re-tailoring the same JD |
| `master_source` | no | Path of the master used, for the audit trail |
| `coverage_pct` | no | Your computed coverage; the script recomputes it and warns on a >2pt mismatch |
| `years_experience` | no | Informational |

## Sections

Headings must be `#` (H1). Recognised names:

| Section | Required | Rendered into the DOCX? | Written to XLSX tab |
|---|---|---|---|
| `Contact` | **yes** | yes | `Master` |
| `Headline` | no | yes (one italic line) | `Master` |
| `Summary` | **yes** | yes | `Master` |
| `Core Skills` | **yes** | yes | `Master` |
| `Experience` | **yes** | yes | `Master` + `Bullets` |
| `Education` | no | yes | `Master` |
| `Certifications` | no | yes | `Master` |
| `JD Mapping` | recommended | **no** | `JD_Mapping` |
| `Keywords` | recommended | **no** | `Keywords` |
| `Gap Analysis` | recommended | **no** | `Gap_Analysis` |

> The three analysis tables never enter the DOCX. They are working data for the user and would
> break ATS parsing if shipped in the resume. This is intentional — see
> [ats-rules.md](ats-rules.md).

### `# Contact`

Three-plus plain lines. Line 1 = name, line 2 = title (optional, **must not contain**
`@ | + /` or a digit), remaining lines = contact details, one per line.

```markdown
# Contact

Ranjeith K
Senior SDET
ranjeith@example.com | +91 90000 00000 | Bengaluru, India | linkedin.com/in/ranjeith
```

### `# Headline`

One line, optional. Rendered as an italic positioning line under the contact block.

```markdown
# Headline

Quality engineering lead - test automation, CI/CD and release confidence at scale
```

### `# Summary`

One or more plain paragraphs (no bullets).

```markdown
# Summary

8 years in test automation and quality engineering, specialising in Playwright/TypeScript
frameworks and CI/CD ownership. Cut release validation from 3 days to 4 hours across 12 services.
Led a 4-engineer automation team through a 400-test Selenium-to-Playwright migration.
```

### `# Core Skills`

Bullets as `- Category: item, item, item`. A bullet with no `:` (or a long prefix) is treated
as a bare skill line.

```markdown
# Core Skills

- Languages: TypeScript, JavaScript, Python, SQL
- Testing: Playwright, Cypress, Selenium WebDriver, RestAssured, Postman
- CI/CD: GitHub Actions, Jenkins, Docker, Kubernetes
- Practices: test automation framework design, shift-left quality, contract testing
```

### `# Experience`

An H2 per role, then `- ` bullets. Heading format:

```
## <Company> | <Title> | <Location> | <Mon YYYY – Mon YYYY>
```

- Field 1 = **organisation**, field 2 = **role**. The renderer displays them flipped as
  `Title | Company`, which is the natural resume order.
- `Location` is optional; the date range is optional but its absence raises a warning.
- Date ranges: `Jan 2020 – Present`, `Mar 2018 - Jun 2020`, or a bare year. Use the en/em dash
  or a plain hyphen — all parse.

```markdown
# Experience

## Acme Corp | Senior SDET | Bengaluru, India | Jan 2021 – Present
- Automated the payments regression suite with Playwright + TypeScript, cutting release validation from 3 days to 4 hours
- Owned GitHub Actions pipelines for 12 services, adding parallel shards that reduced feedback time 60%

## Beta Systems | QA Engineer | Pune, India | Jul 2018 – Dec 2020
- Built a RestAssured + Postman contract suite over 140 endpoints, catching 30+ schema breaks pre-release
```

### `# Education`

Same H2 + bullet shape. Field 1 = institution, field 2 = degree/credential, optional year.

```markdown
# Education

## Anna University | B.E. Computer Science | 2014 – 2018
```

### `# Certifications`

A bullet list.

```markdown
# Certifications

- ISTQB Certified Tester - Advanced Level (2022)
- AWS Certified Cloud Practitioner (2023)
```

### `# JD Mapping`

Markdown table. Header must include `Requirement`, `Priority`, `Coverage`, `Evidence`
(`Where` optional but useful).

- `Priority`: `must-have` or `nice-to-have`. Anything not starting with `nice` counts as must-have.
- `Coverage`: `Direct`, `Partial`, or `Gap` (these exact words — the coverage maths keys off them).

```markdown
# JD Mapping

| Requirement | Priority | Coverage | Evidence | Where |
|---|---|---|---|---|
| Playwright | must-have | Partial | 2 yrs Cypress UI automation, transferable | Summary, Skills |
| TypeScript | must-have | Direct | 4 yrs TypeScript across 3 repos | Summary, Bullets |
| CI/CD (GitHub Actions) | must-have | Direct | Owned pipelines for 12 services | Bullet 2 |
| k6 load testing | nice-to-have | Gap | No load-testing evidence in master | - |
```

Coverage is recomputed as `(Direct + 0.5 × Partial) / must-haves`.

### `# Keywords`

Markdown table. Header must include `Keyword`, `In JD`, `In Master`, `In Tailored`.

```markdown
# Keywords

| Keyword | In JD | In Master | In Tailored | Status |
|---|---|---|---|---|
| Playwright | yes | no | yes | used as Cypress-transferable |
| TypeScript | yes | yes | yes | ok |
| GitHub Actions | yes | yes | yes | ok |
```

The renderer ignores your `In Master` / `In Tailored` claims and **recomputes both** against
`input/master_resume.md` and the tailored resume content, then reports any mismatch. Use
`yes` / `no` in `In JD` — those drive the parity check.

### `# Gap Analysis`

Markdown table. Header must include `Gap`, `Severity`, `Mitigation`.

```markdown
# Gap Analysis

| Gap | Severity | Mitigation |
|---|---|---|
| k6 / load testing | medium | Raise in the cover letter as a learning target; do not claim it |
| No fintech domain exposure | low | Emphasise payments-adjacent work from Acme |
```

## Parsing rules and pitfalls

- **H1 = section, H2 = entry.** A `##` inside `# Experience` starts a new role; a `- ` line is
  its bullet. Don't mix `###`.
- **Bullets need `- `, `* ` or `+ `.** Plain indented text is ignored.
- **Inline bold** with `**text**` is supported in summaries, skills and bullets and renders as
  real bold runs.
- **Don't use markdown tables inside resume sections** — they're only read in the three
  analysis sections.
- **Unknown H1 sections are ignored** with a warning; a misspelled required section fails the
  run with exit code 2.
- A missing `# JD Mapping` / `# Keywords` / `# Gap Analysis` doesn't fail the run, but it
  disables the audit and the report will say so.

## XLSX audit tabs

| Tab | Columns |
|---|---|
| `Master` | Section, Field, Text — the whole tailored resume, editable row by row |
| `JD_Mapping` | Requirement, Priority, Coverage, Evidence, Where (+ coverage footer) |
| `Bullets` | #, Role, Bullet, JD Keywords Hit, Quantified, Starts With Verb |
| `Keywords` | Keyword, In JD, In Master (checked), In Tailored (checked), Status |
| `Gap_Analysis` | Gap, Severity, Mitigation |

`Bullets` is **derived** by the renderer from the experience section, so it can never disagree
with the resume. `Keywords` and the coverage footer are recomputed too — that's the point of
the workbook: it audits the DOCX rather than restating it.

## Console report

Every run prints page estimate, coverage, quantified-bullet ratio, keyword parity, and the
failure/warning lists. Relay it; exit code 2 means a failing check must be fixed and the spec
re-rendered before the resume is sent.
