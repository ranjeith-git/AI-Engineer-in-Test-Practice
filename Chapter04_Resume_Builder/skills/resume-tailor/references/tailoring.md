# Tailoring — how to rewrite the master for one JD

The master is complete; the tailored resume is a **selection and re-wording** of it. Every
sentence you write must trace back to a fact in the master. This file is the rulebook for that
rewrite.

## The one hard rule

> **You may re-word, re-order, re-emphasise and omit. You may never add.**

No invented employers, dates, degrees, certifications, tools, metrics, team sizes, or scope.
Do not promote "familiar with Kubernetes" to "Kubernetes expert". Do not imply ownership of a
team's work. If the JD wants something the master lacks, it becomes a **Gap** in the report —
not a line in the resume.

Everything the user should verify gets surfaced in the Step 8 report.

## Order of work

1. Sort the JD requirements (must-have first, in the JD's own order as a tiebreak).
2. For each role, pick the 3–6 bullets that hit the most must-haves.
3. Rewrite those bullets. Drop the rest.
4. Rebuild the summary from the top few must-haves.
5. Re-order Core Skills so the highest-priority skills lead.
6. Re-estimate length; cut until it fits the page cap.

## Bullet formula

```
<Action verb> + <what you did> + <how / with what> + <measurable outcome>
```

Weak → strong examples:

| Before (master) | After (tailored) |
|---|---|
| Responsible for test automation of the payments module | Automated the payments regression suite with Playwright + TypeScript, cutting release validation from 3 days to 4 hours |
| Worked on CI/CD pipelines | Owned GitHub Actions pipelines for 12 services, adding parallel test shards that reduced feedback time 60% |
| Helped with API testing | Built a RestAssured + Postman contract suite covering 140 endpoints, catching 30+ schema breaks before release |
| Part of the migration team | Migrated 400 legacy Selenium tests to Playwright, removing the flaky-suite quarantine for good |

Rules:

- **Start with an action verb.** Never `Responsible for`, `Worked on`, `Helped with`,
  `Involved in`, `Duties included`, `Participated in`.
- **One idea per bullet.** Two achievements in one bullet lose both.
- **Lead with the outcome when it is the strongest part** — `Reduced flake rate 38% by ...` reads
  better than `Implemented retries to ...`.
- **Keep the master's numbers exactly.** Do not round 38% up to 40%.
- **No first-person pronouns.** No "I", "my", "we".
- **Present tense for the current role, past for previous ones.**
- Aim for one to two wrapped lines each; a three-line bullet is usually two bullets.

### Action verb bank

Automated · Architected · Built · Championed · Consolidated · Designed · Developed · Drove ·
Eliminated · Engineered · Established · Expanded · Implemented · Improved · Increased ·
Introduced · Led · Migrated · Modernised · Optimised · Orchestrated · Owned · Pioneered ·
Reduced · Refactored · Released · Resolved · Restructured · Revamped · Scaled · Shipped ·
Simplified · Spearheaded · Standardised · Streamlined · Strengthened · Transformed · Validated

## Mirror the JD's vocabulary

ATS keyword matching and human reviewers both reward the JD's own phrasing. Use the JD's words
for the same concept — without changing the facts.

| Master says | JD says | Write |
|---|---|---|
| test automation | test automation framework design | Designed a test automation framework ... |
| CI pipelines | Continuous Integration (CI) | ... in CI (GitHub Actions) ... |
| API testing | REST API testing, Postman | REST API testing with Postman + RestAssured |
| shift-left | shift-left quality practices | Shift-left quality practices across 4 squads |
| Selenium | Selenium WebDriver | Selenium WebDriver |

**Always give both the acronym and the expansion once** — "Continuous Integration (CI)",
"Software Development Engineer in Test (SDET)". ATS parsers often look for one or the other.

## Summary

Three to four lines. Formula:

```
<Years> in <the JD's domain>, specialising in <top must-have 1> and <must-have 2>.
<Strongest quantified achievement that matches the JD's biggest pain>.
<What you bring that the JD explicitly asks for - leadership, scale, domain, certification>.
```

- No "seeking a challenging opportunity", no objectives, no first person.
- Put the JD's exact target title in the first line if the master supports it.
- If the JD names a stack you have, name it. If you don't, leave it for the Gap report.

## Core Skills

- One bullet per category from the master (`Languages:`, `Testing:`, `CI/CD:`, `Cloud:`...).
- Re-order categories and items so JD priorities come first.
- Only skills with real evidence in the master. A skill that appears nowhere in Experience is
  a Gap, not a Core Skill.
- Group, don't list 40 items — 5–7 bullets, each 4–8 items.

## What to cut, in order

1. Bullets that hit no JD requirement and no must-have keyword.
2. Roles older than ~15 years, or below the level the JD targets → compress to a one-line entry
   under an `Earlier experience` line, or drop entirely if space is needed.
3. Internal jargon, ticket prefixes, project codenames with no meaning to a stranger.
4. Hobbies, references, photos, "Declaration", date of birth, marital status, full street
   address (city + country is enough), and any statement about salary.
5. Awards/certifications irrelevant to the JD.

**Never cut**: the contact block, employment dates, the most recent role, or anything the JD
explicitly requires.

## Length

| Master evidence | Target |
|---|---|
| < 4 years, or junior JD | 1 page |
| 4–10 years | 1–2 pages |
| 10+ years, senior/lead JD | 2 pages max |

The renderer prints an estimate and fails the check above 2 pages. If you are over: remove
bullets before shrinking the font or margins — the DOCX styling is fixed for ATS safety.

## Phrasing Partial matches honestly

A Partial mapping (adjacent experience) is usable only if the user genuinely did the adjacent
work, and must be phrased as what was actually done:

- Good: `Automated UI regression with Cypress (Playwright transferable)` — only if the user
  agrees with the framing; otherwise just `... with Cypress`.
- Bad: `Playwright expert` when the master has never mentioned Playwright.

When in doubt, keep the tool you actually used and let the cover letter bridge the gap.
