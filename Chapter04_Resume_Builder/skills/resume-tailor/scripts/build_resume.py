#!/usr/bin/env python
"""Render a resume spec (markdown) into an ATS-safe DOCX plus an audit XLSX.

The spec is the contract: the agent writes judgement into it, this script only
renders. It never rewrites, shortens, or "improves" wording.

    python build_resume.py <spec.md> [--out <dir>] [--chapter <dir>] [--check-only]

Exit codes: 0 = ok (warnings allowed), 2 = spec contract violation, 3 = missing
dependency, 1 = unexpected error.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# dependency bootstrap
# --------------------------------------------------------------------------- #

REEXEC_FLAG = "RESUME_TAILOR_REEXEC"


def _chapter_dir(explicit: str | None = None) -> Path:
    """RESUME_ROOT: the folder that holds skills/, input/ and output/."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("RESUME_BUILDER_HOME")
    if env:
        return Path(env).expanduser().resolve()
    # <chapter>/skills/resume-tailor/scripts/build_resume.py
    return Path(__file__).resolve().parents[3]


def _venv_candidates(chapter: Path) -> list[Path]:
    return [
        chapter / ".venv" / "Scripts" / "python.exe",
        chapter / ".venv" / "bin" / "python",
        Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe",
        Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python",
    ]


def _deps_present() -> bool:
    try:
        import docx  # noqa: F401
        import openpyxl  # noqa: F401
    except ImportError:
        return False
    return True


def _require_deps(chapter: Path) -> None:
    """Re-exec under the chapter venv when the active interpreter lacks the deps."""
    if _deps_present():
        return

    if os.environ.get(REEXEC_FLAG) != "1":
        for python in _venv_candidates(chapter):
            if python.exists():
                # subprocess (not os.execv): paths with spaces break execv on Windows.
                env = {**os.environ, REEXEC_FLAG: "1"}
                completed = subprocess.run(
                    [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                    env=env,
                )
                sys.exit(completed.returncode)

    exe = sys.executable
    sys.stderr.write(
        "ERROR: python-docx and openpyxl are required but missing from\n"
        f"       {exe}\n\n"
        "Create the chapter environment once, then re-run:\n\n"
        f'  "{exe}" -m venv "{chapter / ".venv"}"\n'
        f'  "{chapter / ".venv" / "Scripts" / "python.exe"}" -m pip install -r '
        f'"{chapter / "requirements.txt"}"\n'
    )
    sys.exit(3)


# --------------------------------------------------------------------------- #
# spec parsing
# --------------------------------------------------------------------------- #

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
DATE_RANGE_RE = re.compile(r"(\d{4}|present|current)", re.IGNORECASE)
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
DATE_TOKEN_RE = re.compile(rf"^(?:{MONTHS})[a-z]*\.?\s*\d{{4}}$", re.IGNORECASE)

REQUIRED_SECTIONS = ("Contact", "Summary", "Core Skills", "Experience")
KNOWN_SECTIONS = (
    "Contact",
    "Headline",
    "Summary",
    "Core Skills",
    "Experience",
    "Education",
    "Certifications",
    "JD Mapping",
    "Keywords",
    "Gap Analysis",
)
ANALYSIS_SECTIONS = ("JD Mapping", "Keywords", "Gap Analysis")
RESUME_SECTIONS = ("Headline", "Summary", "Core Skills", "Experience", "Education", "Certifications")

ACTION_VERBS = {
    "achieved", "architected", "automated", "built", "championed", "collaborated", "conducted",
    "consolidated", "created", "defined", "delivered", "designed", "developed", "diagnosed",
    "directed", "drove", "eliminated", "engineered", "established", "executed", "expanded",
    "improved", "increased", "implemented", "initiated", "introduced", "led", "managed",
    "measured", "migrated", "mentored", "modernised", "modernized", "optimised", "optimized",
    "orchestrated", "owned", "partnered", "pioneered", "planned", "prevented", "prioritised",
    "prioritized", "produced", "ran", "rearchitected", "reduced", "refactored", "released",
    "resolved", "restructured", "revamped", "scaled", "shipped", "simplified", "spearheaded",
    "standardised", "standardized", "streamlined", "strengthened", "supported", "tested",
    "trained", "transformed", "validated", "wrote",
    "containerised", "containerized", "cut", "hardened", "instrumented", "mapped", "rolled",
    "remediated", "reviewed", "seeded", "stabilised", "stabilized", "unified",
}

TITLE_WORDS = (
    "engineer", "developer", "manager", "analyst", "lead", "sdet", "tester", "architect",
    "consultant", "specialist", "director", "intern", "qa ", "scientist", "designer",
)


def _looks_like_title(text: str) -> bool:
    """Heuristic guard: the H2 order is 'Company | Title', so field 1 should be an employer."""
    lowered = f" {text.lower()} "
    return any(word in lowered for word in TITLE_WORDS)


class SpecError(Exception):
    """The spec breaks the renderer contract."""


def strip_comments(text: str) -> str:
    """Drop HTML comments: they hold notes ('no Playwright experience'), not evidence."""
    return HTML_COMMENT_RE.sub(" ", text)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SpecError(
            "missing YAML frontmatter - the spec must start with --- block --- "
            "containing at least candidate and target_role."
        )
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise SpecError(f"invalid frontmatter line (expected 'key: value'): {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    if not meta.get("candidate"):
        raise SpecError("frontmatter must set 'candidate'")
    if not meta.get("target_role"):
        raise SpecError("frontmatter must set 'target_role'")
    return meta, text[match.end():]


def _split_sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in body.splitlines():
        line = raw.rstrip()
        h1 = H1_RE.match(line)
        if h1:
            name = h1.group(1).strip()
            canonical = next((s for s in KNOWN_SECTIONS if s.lower() == name.lower()), name)
            current = canonical
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def parse_contact(lines: list[str]) -> dict[str, str]:
    filled = [ln.strip() for ln in lines if ln.strip()]
    if not filled:
        raise SpecError("'# Contact' section is empty (need name / title / contact line)")
    contact = {"name": filled[0], "title": "", "details": []}
    rest = filled[1:]
    if rest and not any(tok in rest[0] for tok in ("@", "|", "http", "+", "/")) and not any(
        ch.isdigit() for ch in rest[0]
    ):
        contact["title"] = rest.pop(0)
    contact["details"] = rest
    return contact


BULLET_PREFIXES = ("- ", "* ", "+ ")


def _is_bullet(line: str) -> bool:
    return line.strip().startswith(BULLET_PREFIXES)


def _merge_continuations(lines: list[str]) -> list[str]:
    """Join soft-wrapped source lines so a bullet wrapped over two lines stays one bullet."""
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(BULLET_PREFIXES):
            items.append(stripped[2:].strip())
        elif items:
            items[-1] = f"{items[-1]} {stripped}"
    return items


def parse_bullets(lines: list[str]) -> list[str]:
    return [item for item in _merge_continuations(lines) if item]


def parse_paragraphs(lines: list[str]) -> list[str]:
    """Blank line = new paragraph; a soft wrap inside a paragraph is joined, not split."""
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append(" ".join(buffer))
                buffer = []
            continue
        if stripped.startswith(("|", "#")) or _is_bullet(stripped):
            continue
        buffer.append(stripped)
    if buffer:
        paragraphs.append(" ".join(buffer))
    return paragraphs


def parse_skills(lines: list[str]) -> list[tuple[str, str]]:
    """Return [(category, items)] - a bare bullet yields ('', text)."""
    skills: list[tuple[str, str]] = []
    for entry in _merge_continuations(lines):
        if ":" in entry:
            category, items = entry.split(":", 1)
            if 0 < len(category) <= 32:
                skills.append((category.strip(), items.strip()))
                continue
        skills.append(("", entry))
    return skills


def parse_experience(lines: list[str]) -> list[dict]:
    roles: list[dict] = []
    current: dict | None = None
    for line in lines:
        stripped = line.strip()
        h2 = H2_RE.match(stripped)
        if h2:
            parts = [p.strip() for p in h2.group(1).split("|")]
            dates = ""
            if parts and DATE_RANGE_RE.search(parts[-1]) and not DATE_TOKEN_RE.match(parts[-1]):
                dates = parts.pop()
            if parts and DATE_TOKEN_RE.match(parts[-1]):
                dates = parts.pop()
            location = ""
            if len(parts) > 2:
                location = parts.pop()
            company = parts[0] if parts else ""
            title = parts[1] if len(parts) > 1 else ""
            current = {
                "company": company,
                "title": title,
                "location": location,
                "dates": dates,
                "bullets": [],
            }
            roles.append(current)
            continue
        if current is not None and stripped.startswith(BULLET_PREFIXES):
            current["bullets"].append(stripped[2:].strip())
        elif current is not None and stripped and current["bullets"]:
            # soft-wrapped bullet: a continuation line belongs to the previous bullet
            current["bullets"][-1] = f"{current['bullets'][-1]} {stripped}"
    return roles


def parse_table(lines: list[str], expected_header: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} and c for c in cells):
            continue
        if not header:
            header = cells
            continue
        row = {header[i] if i < len(header) else f"col{i}": cells[i] if i < len(cells) else ""
               for i in range(max(len(header), len(cells)))}
        if any(v.strip() for v in row.values()):
            rows.append(row)
    if header:
        missing = [h for h in expected_header if h not in header]
        if missing:
            raise SpecError(
                f"table header must contain {expected_header}; missing {missing} (found {header})"
            )
    return rows


def parse_spec(text: str) -> dict:
    meta, body = parse_frontmatter(text)
    sections = _split_sections(body)

    unknown = [s for s in sections if s not in KNOWN_SECTIONS]
    missing = [s for s in REQUIRED_SECTIONS if s not in sections or not any(l.strip() for l in sections[s])]
    if missing:
        raise SpecError(
            f"missing/empty required section(s): {missing}. "
            f"Allowed H1 headings: {list(KNOWN_SECTIONS)}"
        )

    spec: dict = {"meta": meta, "sections": sections, "warnings": [], "section_order": []}
    if unknown:
        spec["warnings"].append(f"ignored unknown section(s): {unknown}")

    spec["contact"] = parse_contact(sections["Contact"])
    spec["headline"] = next((ln.strip() for ln in sections.get("Headline", []) if ln.strip()), "")
    spec["summary"] = parse_paragraphs(sections["Summary"])
    spec["skills"] = parse_skills(sections["Core Skills"])
    spec["experience"] = parse_experience(sections["Experience"])
    spec["education"] = parse_experience(sections.get("Education", []))
    spec["certifications"] = parse_bullets(sections.get("Certifications", []))
    spec["jd_mapping"] = parse_table(
        sections.get("JD Mapping", []),
        ["Requirement", "Priority", "Coverage", "Evidence"],
    )
    spec["keywords"] = parse_table(
        sections.get("Keywords", []),
        ["Keyword", "In JD", "In Master", "In Tailored"],
    )
    spec["gaps"] = parse_table(sections.get("Gap Analysis", []), ["Gap", "Severity", "Mitigation"])

    if not spec["summary"]:
        raise SpecError("'# Summary' must contain at least one paragraph")
    if any(_is_bullet(line) for line in sections["Summary"]):
        spec["warnings"].append("bullets in '# Summary' are ignored - write plain paragraphs there")
    if not spec["skills"]:
        raise SpecError("'# Core Skills' must contain at least one bullet")
    if not spec["experience"]:
        raise SpecError("'# Experience' must contain at least one '## Company | Title | Location | Mon YYYY - Mon YYYY' entry")
    for role in spec["experience"]:
        if not role["bullets"]:
            spec["warnings"].append(f"role '{role['company']}' has no bullets")
        if not role["dates"]:
            spec["warnings"].append(
                f"role '{role['company']}' has no parseable date range (use 'Mon YYYY - Mon YYYY' or 'Present')"
            )
        if _looks_like_title(role["company"]):
            spec["warnings"].append(
                f"experience heading '{role['company']}' reads like a job title - the order is "
                "'## Company | Title | Location | Mon YYYY - Mon YYYY'"
            )
    return spec


# --------------------------------------------------------------------------- #
# derived audit facts
# --------------------------------------------------------------------------- #

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*")


def _keyword_hits(text: str, keyword: str) -> bool:
    if not keyword or not text:
        return False
    if re.search(r"\s", keyword):
        return keyword.lower() in text.lower()
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def _stem_forms(word: str) -> set[str]:
    """Light stemming so 'mentoring' matches 'Mentored' in the master."""
    word = word.lower()
    forms = {word}
    if word.endswith("ing") and len(word) > 5:
        forms.update({word[:-3], word[:-3] + "e"})
    if word.endswith("ed") and len(word) > 4:
        forms.update({word[:-2], word[:-1]})
    if word.endswith("s") and len(word) > 4:
        forms.add(word[:-1])
    return forms


def _evidence_hits(text: str, keyword: str) -> bool:
    """Relaxed provenance match: is this claim supported anywhere in the master?

    ATS keyword matching must be literal (a parser looks for the exact string), but
    provenance checking is semantic - the master may say 'Mentored' where the resume
    says 'mentoring'. Short tokens (< 4 chars, e.g. 'k6') stay exact so the
    fabrication guard is not weakened.
    """
    if not keyword or not text:
        return False
    if _keyword_hits(text, keyword):
        return True
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", keyword) if len(w) > 3]
    if not words:
        return False
    haystack = text.lower()
    for word in words:
        if not any(re.search(rf"(?<![a-z0-9]){re.escape(form)}", haystack) for form in _stem_forms(word)):
            return False
    return True


def tailored_resume_text(spec: dict) -> str:
    parts = [spec["contact"]["name"], spec["contact"]["title"] or spec["meta"]["target_role"], spec["headline"]]
    parts += spec["summary"]
    parts += [f"{cat} {items}" for cat, items in spec["skills"]]
    for role in spec["experience"]:
        parts += [role["company"], role["title"], *role["bullets"]]
    for role in spec["education"]:
        parts += [role["company"], role["title"], *role["bullets"]]
    parts += spec["certifications"]
    return "\n".join(p for p in parts if p)


def is_quantified(text: str) -> bool:
    return re.search(r"\d", text) is not None


def build_bullet_audit(spec: dict, keywords: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    index = 0
    for role in spec["experience"]:
        label = " - ".join(p for p in (role["title"], role["company"]) if p)
        for bullet in role["bullets"]:
            index += 1
            hits = [kw for kw in keywords if _keyword_hits(bullet, kw)]
            first = WORD_RE.search(bullet)
            verb_ok = bool(first) and first.group(0).lower() in ACTION_VERBS
            rows.append(
                {
                    "#": str(index),
                    "Role": label,
                    "Bullet": bullet,
                    "JD Keywords Hit": ", ".join(hits),
                    "Quantified": "yes" if is_quantified(bullet) else "NO",
                    "Starts With Verb": "yes" if verb_ok else f"NO ({first.group(0) if first else '?'})",
                }
            )
    return rows


def compute_coverage(mapping: list[dict[str, str]]) -> dict:
    must = direct = partial = gap = 0
    points = 0.0
    for row in mapping:
        priority = (row.get("Priority") or "").strip().lower()
        if priority.startswith("nice"):
            continue
        coverage = (row.get("Coverage") or "").strip().lower()
        must += 1
        if coverage.startswith("direct"):
            direct += 1
            points += 1
        elif coverage.startswith("partial"):
            partial += 1
            points += 0.5
        else:
            gap += 1
    pct = round(100 * points / must) if must else 0
    return {"must": must, "direct": direct, "partial": partial, "gap": gap, "pct": pct}


def estimate_pages(spec: dict) -> float:
    """Rough page estimate from wrapped-line maths at Calibri 10.5pt / 0.6in margins."""
    usable_height = 792 - 2 * 43.2
    body_line = 13.0
    total = 0.0

    def add(text: str, chars_per_line: int, line_height: float, spacing: float = 0.0) -> None:
        nonlocal total
        if not text:
            return
        wrapped = max(1, math.ceil(len(text) / chars_per_line))
        total += wrapped * line_height + spacing

    add(spec["contact"]["name"], 60, 22.0, 4)
    add(spec["contact"]["title"] or spec["meta"]["target_role"], 80, 14.0, 2)
    for line in spec["contact"]["details"]:
        add(line, 100, body_line, 2)
    add(spec["headline"], 100, body_line, 4)

    def heading() -> None:
        nonlocal total
        total += 11 + 12 + 4

    if spec["summary"]:
        heading()
        for para in spec["summary"]:
            add(para, 100, body_line, 4)
    if spec["skills"]:
        heading()
        for category, items in spec["skills"]:
            add(f"{category}: {items}" if category else items, 92, body_line, 3)
    if spec["experience"]:
        heading()
        for role in spec["experience"]:
            add(f"{role['title']} {role['company']} {role['location']} {role['dates']}", 95, body_line, 3)
            for bullet in role["bullets"]:
                add(bullet, 90, body_line, 3)
    if spec["education"]:
        heading()
        for role in spec["education"]:
            add(f"{role['title']} {role['company']} {role['dates']}", 95, body_line, 3)
            for bullet in role["bullets"]:
                add(bullet, 90, body_line, 3)
    if spec["certifications"]:
        heading()
        for cert in spec["certifications"]:
            add(cert, 92, body_line, 3)
    return round(total / usable_height, 1)


# --------------------------------------------------------------------------- #
# DOCX rendering
# --------------------------------------------------------------------------- #

def render_docx(spec: dict, path: Path) -> None:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt

    usable_width = 7.3
    doc = Document()

    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.6)
    section.left_margin = section.right_margin = Inches(0.6)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0

    for style_name in ("List Bullet",):
        style = doc.styles[style_name]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)
        style.paragraph_format.space_after = Pt(2)
        style.paragraph_format.line_spacing = 1.0

    def add_runs(paragraph, text: str) -> None:
        for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if not chunk:
                continue
            run = paragraph.add_run(chunk)
            run.bold = i % 2 == 1

    def add_paragraph(text: str, *, size: float = 10.5, bold: bool = False,
                      align=None, space_before: float = 0.0, space_after: float = 0.0,
                      italic: bool = False, style: str | None = None):
        paragraph = doc.add_paragraph(style=style) if style else doc.add_paragraph()
        if align is not None:
            paragraph.alignment = align
        paragraph.paragraph_format.space_before = Pt(space_before)
        paragraph.paragraph_format.space_after = Pt(space_after)
        if style is None:
            for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
                if not chunk:
                    continue
                run = paragraph.add_run(chunk)
                run.bold = bold or i % 2 == 1
                run.italic = italic
                run.font.size = Pt(size)
        else:
            add_runs(paragraph, text)
            for run in paragraph.runs:
                run.font.size = Pt(size)
                run.italic = italic
        return paragraph

    def add_heading(text: str) -> None:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(11)
        paragraph.paragraph_format.space_after = Pt(4)
        run = paragraph.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(11.5)
        ppr = paragraph._p.get_or_add_pPr()
        borders = ppr.makeelement(qn("w:pBdr"), {})
        bottom = borders.makeelement(
            qn("w:bottom"),
            {qn("w:val"): "single", qn("w:sz"): "6", qn("w:space"): "1", qn("w:color"): "808080"},
        )
        borders.append(bottom)
        ppr.append(borders)

    def add_bullet(text: str) -> None:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.left_indent = Inches(0.22)
        add_runs(paragraph, text)
        for run in paragraph.runs:
            run.font.size = Pt(10.5)

    def add_role_line(left: str, right: str) -> None:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            Inches(usable_width), WD_TAB_ALIGNMENT.RIGHT
        )
        run = paragraph.add_run(left)
        run.bold = True
        run.font.size = Pt(10.5)
        if right:
            tab_run = paragraph.add_run("\t" + right)
            tab_run.font.size = Pt(10.5)
            tab_run.italic = True

    contact = spec["contact"]
    add_paragraph(contact["name"], size=19, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    title = contact["title"] or spec["meta"]["target_role"]
    add_paragraph(title, size=11.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    for line in contact["details"]:
        add_paragraph(line, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=1)
    if spec["headline"]:
        add_paragraph(spec["headline"], size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                      italic=True, space_before=2, space_after=2)

    if spec["summary"]:
        add_heading("Summary")
        for paragraph in spec["summary"]:
            add_paragraph(paragraph, space_after=3)

    if spec["skills"]:
        add_heading("Core Skills")
        for category, items in spec["skills"]:
            add_bullet(f"**{category}:** {items}" if category else items)

    if spec["experience"]:
        add_heading("Experience")
        for role in spec["experience"]:
            add_role_line(" | ".join(p for p in (role["title"], role["company"]) if p), role["dates"])
            if role["location"]:
                add_paragraph(role["location"], size=9.5, italic=True, space_after=2)
            for bullet in role["bullets"]:
                add_bullet(bullet)

    if spec["education"]:
        add_heading("Education")
        for role in spec["education"]:
            add_role_line(" | ".join(p for p in (role["title"], role["company"]) if p), role["dates"])
            for bullet in role["bullets"]:
                add_bullet(bullet)

    if spec["certifications"]:
        add_heading("Certifications")
        for cert in spec["certifications"]:
            add_bullet(cert)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))


# --------------------------------------------------------------------------- #
# XLSX rendering
# --------------------------------------------------------------------------- #

def render_xlsx(spec: dict, path: Path, *, coverage: dict, bullets: list[dict], keywords: list[str],
                master_text: str | None) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    head_font = Font(bold=True, color="FFFFFF", size=11)
    head_fill = PatternFill("solid", fgColor="1F3864")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = Workbook()

    def write_sheet(ws, headers: list[str], rows: list[list[str]], widths: list[int],
                    wrap_cols: tuple[int, ...] = ()) -> None:
        ws.append(headers)
        for cell in ws[1]:
            cell.font = head_font
            cell.fill = head_fill
            cell.alignment = Alignment(vertical="center", horizontal="left")
        for row in rows:
            ws.append(row)
        for idx, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width
        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=cell.column in wrap_cols)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    # --- Master: the editable working copy of the resume --------------------- #
    ws = wb.active
    ws.title = "Master"
    master_rows: list[list[str]] = [
        ["Contact", "Name", spec["contact"]["name"]],
        ["Contact", "Target title", spec["contact"]["title"] or spec["meta"]["target_role"]],
    ]
    for line in spec["contact"]["details"]:
        master_rows.append(["Contact", "Detail", line])
    if spec["headline"]:
        master_rows.append(["Headline", "", spec["headline"]])
    for para in spec["summary"]:
        master_rows.append(["Summary", "", para])
    for category, items in spec["skills"]:
        master_rows.append(["Core Skills", category or "Skills", items])
    for role in spec["experience"]:
        master_rows.append(["Experience", "Role", f"{role['title']} | {role['company']}"])
        master_rows.append(["Experience", "Location", role["location"]])
        master_rows.append(["Experience", "Dates", role["dates"]])
        for bullet in role["bullets"]:
            master_rows.append(["Experience", "Bullet", bullet])
    for role in spec["education"]:
        master_rows.append(["Education", "Entry", f"{role['title']} | {role['company']} | {role['dates']}"])
        for bullet in role["bullets"]:
            master_rows.append(["Education", "Bullet", bullet])
    for cert in spec["certifications"]:
        master_rows.append(["Certifications", "", cert])
    write_sheet(ws, ["Section", "Field", "Text"], master_rows, [16, 16, 120], wrap_cols=(3,))

    # --- JD_Mapping ---------------------------------------------------------- #
    mapping_rows = [
        [
            row.get("Requirement", ""),
            row.get("Priority", ""),
            row.get("Coverage", ""),
            row.get("Evidence", ""),
            row.get("Where", ""),
        ]
        for row in spec["jd_mapping"]
    ]
    mapping_rows.append([])
    mapping_rows.append([
        "COVERAGE (must-have)",
        f"{coverage['pct']}%",
        f"{coverage['direct']} Direct / {coverage['partial']} Partial / {coverage['gap']} Gap",
        f"{coverage['must']} must-have requirements",
        f"frontmatter said {spec['meta'].get('coverage_pct', 'n/a')}",
    ])
    write_sheet(
        wb.create_sheet("JD_Mapping"),
        ["Requirement", "Priority", "Coverage", "Evidence", "Where"],
        mapping_rows,
        [40, 12, 12, 60, 26],
        wrap_cols=(1, 4, 5),
    )

    # --- Bullets ------------------------------------------------------------- #
    write_sheet(
        wb.create_sheet("Bullets"),
        ["#", "Role", "Bullet", "JD Keywords Hit", "Quantified", "Starts With Verb"],
        [[r["#"], r["Role"], r["Bullet"], r["JD Keywords Hit"], r["Quantified"], r["Starts With Verb"]]
         for r in bullets],
        [5, 32, 95, 32, 11, 16],
        wrap_cols=(2, 3, 4),
    )

    # --- Keywords ------------------------------------------------------------ #
    keyword_rows: list[list[str]] = []
    for row in spec["keywords"]:
        keyword = row.get("Keyword", "")
        computed_master = "yes" if master_text is not None and _evidence_hits(master_text, keyword) else (
            "unknown" if master_text is None else "NO"
        )
        computed_tailored = "yes" if _keyword_hits(tailored_resume_text(spec), keyword) else "NO"
        declared_tailored = (row.get("In Tailored") or "").strip().lower() or computed_tailored
        status = "ok"
        if computed_tailored == "yes" and computed_master == "NO":
            status = "REVIEW: not found in master"
        elif (row.get("In JD") or "").strip().lower().startswith("y") and computed_tailored == "NO":
            status = "missing from resume"
        elif declared_tailored != computed_tailored:
            status = f"declared {declared_tailored}, actual {computed_tailored}"
        keyword_rows.append([
            keyword,
            row.get("In JD", ""),
            computed_master,
            computed_tailored,
            status,
        ])
    write_sheet(
        wb.create_sheet("Keywords"),
        ["Keyword", "In JD", "In Master (checked)", "In Tailored (checked)", "Status"],
        keyword_rows,
        [30, 8, 20, 22, 30],
        wrap_cols=(1, 5),
    )

    # --- Gap_Analysis -------------------------------------------------------- #
    write_sheet(
        wb.create_sheet("Gap_Analysis"),
        ["Gap", "Severity", "Mitigation"],
        [[r.get("Gap", ""), r.get("Severity", ""), r.get("Mitigation", "")] for r in spec["gaps"]],
        [38, 12, 90],
        wrap_cols=(1, 3),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

def verify(spec: dict, *, coverage: dict, bullets: list[dict], keywords: list[str],
           master_text: str | None, pages: float) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    contact_text = " ".join([spec["contact"]["name"], *spec["contact"]["details"]])
    if "@" not in contact_text:
        failures.append("no email address in the Contact block")
    if not re.search(r"(\+\d[\d\s().-]{6,}|\d{3}[\s.-]?\d{3}[\s.-]?\d{4})", contact_text):
        warnings.append("no phone number detected in the Contact block")
    if "linkedin" not in contact_text.lower():
        warnings.append("no LinkedIn URL in the Contact block")

    if pages > 2.4:
        failures.append(f"estimated length {pages} pages is over the 2-page cap - cut content")
    elif pages > 2.0:
        warnings.append(f"estimated length {pages} pages - trim so it lands inside 2 pages")

    if not spec["jd_mapping"]:
        warnings.append("'# JD Mapping' table is empty - coverage cannot be audited")
    elif coverage["must"] == 0:
        warnings.append("no must-have requirements found in '# JD Mapping' (check the Priority column)")

    declared = spec["meta"].get("coverage_pct")
    if declared:
        try:
            if abs(float(declared) - coverage["pct"]) > 2:
                warnings.append(
                    f"frontmatter coverage_pct {declared} != recomputed {coverage['pct']}%; "
                    "the recomputed value wins"
                )
        except ValueError:
            warnings.append(f"frontmatter coverage_pct '{declared}' is not a number")

    if bullets:
        unquantified = [b["#"] for b in bullets if b["Quantified"] != "yes"]
        ratio = round(100 * (len(bullets) - len(unquantified)) / len(bullets))
        if ratio < 40:
            warnings.append(
                f"only {ratio}% of bullets contain a number (target 60%+) - "
                f"unquantified bullets: {', '.join(unquantified)}"
            )
        weak = [b["#"] for b in bullets if b["Starts With Verb"].startswith("NO")]
        if weak:
            warnings.append(f"bullets not starting with an action verb: {', '.join(weak)}")
    else:
        warnings.append("no experience bullets found")

    direct_claims = " ".join(
        f"{row.get('Requirement', '')} {row.get('Evidence', '')}"
        for row in spec["jd_mapping"]
        if (row.get("Coverage") or "").strip().lower().startswith("direct")
    )
    claimed_but_missing: list[str] = []
    jd_kw_missing: list[str] = []
    for row in spec["keywords"]:
        keyword = row.get("Keyword", "")
        if not (row.get("In JD") or "").strip().lower().startswith("y"):
            continue
        if _keyword_hits(tailored_resume_text(spec), keyword):
            continue
        if _keyword_hits(direct_claims, keyword):
            claimed_but_missing.append(keyword)
        else:
            jd_kw_missing.append(keyword)
    if claimed_but_missing:
        failures.append(
            f"claimed 'Direct' in '# JD Mapping' but absent from the resume: {claimed_but_missing}"
        )
    if jd_kw_missing:
        warnings.append(f"JD keywords not in the resume (expected for gaps): {jd_kw_missing}")

    if master_text is None:
        warnings.append("master resume not found - keyword provenance could not be checked")
    else:
        for row in spec["keywords"]:
            keyword = row.get("Keyword", "")
            if _keyword_hits(tailored_resume_text(spec), keyword) and not _evidence_hits(master_text, keyword):
                warnings.append(
                    f"REVIEW '{keyword}' appears in the tailored resume but not in the master - "
                    "confirm it is true before sending"
                )
        for role in spec["experience"]:
            if role["company"] and not _evidence_hits(master_text, role["company"].split()[0]):
                warnings.append(f"REVIEW employer '{role['company']}' not found in the master")

    if not spec["gaps"]:
        warnings.append("'# Gap Analysis' is empty - list what the JD wants and the master lacks")
    if not spec["certifications"]:
        warnings.append("no Certifications section (fine if the master has none)")
    return failures, warnings


def report(spec: dict, *, coverage: dict, bullets: list[dict], pages: float,
           failures: list[str], warnings: list[str], docx_path: Path, xlsx_path: Path,
           keys: list[str]) -> None:
    meta = spec["meta"]
    quantified = sum(1 for b in bullets if b["Quantified"] == "yes")
    parity = 0
    if keys:
        hit = sum(1 for kw in keys if _keyword_hits(tailored_resume_text(spec), kw))
        parity = round(100 * hit / len(keys))

    def line(text: str = "") -> None:
        print(text)

    line("=" * 72)
    line(f"RESUME TAILORED - {meta['candidate']} -> {meta['target_role']}"
         f"{' @ ' + meta['company'] if meta.get('company') else ''} ({meta.get('version', 'v1')})")
    line("=" * 72)
    line(f"DOCX            : {docx_path}")
    line(f"XLSX audit      : {xlsx_path}")
    line(f"Length          : ~{pages} page(s)  (cap: 2)")
    line(f"Coverage        : {coverage['pct']}% of {coverage['must']} must-haves "
         f"({coverage['direct']} direct, {coverage['partial']} partial, {coverage['gap']} gap)")
    line(f"Bullets         : {len(bullets)} total, {quantified} quantified "
         f"({round(100 * quantified / len(bullets)) if bullets else 0}%)")
    line(f"Keyword parity  : {parity}% ({len(keys)} keywords tracked)")
    line(f"ATS structure   : single column, no tables/images in body, standard headings - OK")
    line("-" * 72)
    if failures:
        line(f"FAILED CHECKS ({len(failures)}) - fix the spec and re-render:")
        for item in failures:
            line(f"  [FAIL] {item}")
    if warnings:
        line(f"WARNINGS ({len(warnings)}):")
        for item in warnings:
            line(f"  [WARN] {item}")
    if not failures and not warnings:
        line("No issues found.")
    line("-" * 72)
    line("Relay this report to the user and flag every REVIEW item for confirmation.")
    line("=" * 72)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spec", help="path to the resume spec markdown file")
    parser.add_argument("--out", help="output directory (default: alongside the spec)")
    parser.add_argument("--chapter", help="RESUME_ROOT override (default: the folder holding skills/)")
    parser.add_argument("--check-only", action="store_true", help="validate and report, write nothing")
    parser.add_argument("--docx-name", default="resume.docx")
    parser.add_argument("--xlsx-name", default="resume_audit.xlsx")
    args = parser.parse_args(argv)

    chapter = _chapter_dir(args.chapter)
    _require_deps(chapter)

    spec_path = Path(args.spec).expanduser().resolve()
    if not spec_path.exists():
        print(f"ERROR: spec not found: {spec_path}", file=sys.stderr)
        return 2

    try:
        text = strip_comments(spec_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR: cannot read spec: {exc}", file=sys.stderr)
        return 2

    try:
        spec = parse_spec(text)
    except SpecError as exc:
        print(f"SPEC ERROR: {exc}", file=sys.stderr)
        return 2

    master_path = chapter / "input" / "master_resume.md"
    if not master_path.exists():
        declared = spec["meta"].get("master_source")
        if declared:
            candidate = Path(declared)
            if not candidate.is_absolute():
                candidate = chapter / candidate
            if candidate.exists():
                master_path = candidate
    master_text = None
    if master_path.exists():
        try:
            master_text = strip_comments(master_path.read_text(encoding="utf-8"))
        except OSError as exc:
            spec["warnings"].append(f"could not read master resume: {exc}")

    keywords = [r.get("Keyword", "").strip() for r in spec["keywords"] if r.get("Keyword", "").strip()]
    coverage = compute_coverage(spec["jd_mapping"])
    bullets = build_bullet_audit(spec, keywords)
    pages = estimate_pages(spec)

    out_dir = Path(args.out).expanduser().resolve() if args.out else spec_path.parent
    docx_path = out_dir / args.docx_name
    xlsx_path = out_dir / args.xlsx_name

    failures, warnings = verify(
        spec, coverage=coverage, bullets=bullets, keywords=keywords,
        master_text=master_text, pages=pages,
    )
    warnings = spec["warnings"] + warnings

    if not args.check_only:
        try:
            render_docx(spec, docx_path)
            render_xlsx(spec, xlsx_path, coverage=coverage, bullets=bullets,
                        keywords=keywords, master_text=master_text)
        except Exception as exc:  # noqa: BLE001 - surface renderer faults verbatim
            print(f"RENDER ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1

    report(spec, coverage=coverage, bullets=bullets, pages=pages, failures=failures,
           warnings=warnings, docx_path=docx_path, xlsx_path=xlsx_path, keys=keywords)

    return 2 if failures else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best effort on legacy consoles
        pass
    sys.exit(main())
