# ATS rules — the constraints the renderer enforces and you must not break

Applicant Tracking Systems parse a resume into fields before a human ever sees it. Anything
that breaks parsing loses the application. The renderer's DOCX is ATS-safe **by construction**;
your job is to not defeat it with the spec.

## Layout rules (already handled by `build_resume.py`)

| Rule | Why |
|---|---|
| Single column | Multi-column layouts interleave text on parse |
| **No tables in the resume body** | Table cells are frequently dropped or scrambled |
| No text boxes, shapes, images, icons, photos | Often skipped entirely, and photos carry bias risk |
| No headers/footers carrying content | Many parsers ignore them — contact details vanish |
| Standard fonts (Calibri), 10.5pt body, 0.6" margins | Readable and parseable |
| Real Word bullet lists | Not pasted `•` glyphs, which can merge bullets into one blob |
| Section headings as plain ALL-CAPS paragraphs with a bottom border | Not Word "Heading 1" styles that some parsers treat as page structure |
| Dates as `MMM YYYY` | `03/04/2020` is ambiguous (3 April vs 4 March); `2020–Present` parses reliably |
| Right-aligned dates via tab stops | Keeps the date on the same line without a table |

The analysis tables — `JD Mapping`, `Keywords`, `Gap Analysis` — are deliberately **excluded**
from the DOCX and written only to the XLSX. They are working documents for the user, and they
would wreck ATS parsing if they shipped inside the resume.

## Contact block

Required: **name, email, phone, city + country**. Expected: LinkedIn URL. The renderer fails
the check when the email is missing and warns on a missing phone or LinkedIn.

- Write the email as plain text (`name@example.com`), never as a hyperlink-only field or an image.
- `City, Country` is enough — skip the full street address.
- Omit date of birth, marital status, nationality, photo, and "Declaration" blocks.

## Keywords

The JD's exact strings are the evidence. For each must-have requirement:

1. **Use the JD's own term**, not a synonym: if it says "test automation framework design",
   don't write "automation".
2. **Include both the acronym and the expansion once**: `Continuous Integration (CI)`,
   `Software Development Engineer in Test (SDET)`, `Application Programming Interface (API)`.
3. **Repeat a must-have keyword 2–3 times across the resume** (summary, skills, one bullet) —
   enough to register as a match, not so much that it reads as stuffed. Never keyword-stuff a
   list that has no supporting bullet.
4. **Spell out tools as the JD does**: `Selenium WebDriver` if that's the JD's phrasing,
   `GitHub Actions` not `GHA`.

The `Keywords` tab in the XLSX is recomputed against the real master and the real tailored text
by the renderer — a keyword marked `In JD = yes` that never appears in the resume is a **hard
failure**, and a keyword that appears in the resume but not the master is flagged `REVIEW`.
That second check is the guard against accidental fabrication.

## Section headings

Recognised by most parsers: `SUMMARY`, `PROFESSIONAL SUMMARY`, `CORE SKILLS`, `SKILLS`,
`EXPERIENCE`, `WORK EXPERIENCE`, `PROFESSIONAL EXPERIENCE`, `EDUCATION`, `CERTIFICATIONS`.

Avoid: `My Journey`, `Where I've Been`, `Toolbox`, `Tech Stack I Love` — creative headings hide
whole sections from the parser.

## File naming and format

- Submit `.docx` or a PDF **exported from that DOCX** — never a scan, never an image.
- Name the file `<Firstname>_<Lastname>_<Role>.docx` when the application asks for a resume
  file, e.g. `Ranjeith_K_Senior_SDET.docx`. The renderer keeps `resume.docx` inside the audit
  folder; rename the copy you submit.
- Don't add a password, and don't compress into `.zip` unless asked.

## What the renderer checks on every run

- required sections present → **fail** if missing
- email present, phone/LinkedIn present → fail / warn
- estimated length ≤ 2 pages → **fail** if over; warn near the cap
- every `In JD = yes` keyword present in the resume → **fail** if missing
- keyword present in resume but absent in master → **warn** (confirm it's true)
- employer named in the resume but not found in the master → **warn**
- quantified-bullet ratio ≥ 40% → warn below (target 60%+)
- bullets starting with an action verb → warn per offending bullet
- `Gap Analysis` present and non-empty → warn if empty

Failures exit with code 2; fix the spec and re-render, don't ship a failing report.
