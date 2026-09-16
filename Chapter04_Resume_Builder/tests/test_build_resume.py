"""Tests for the resume-tailor renderer (skills/resume-tailor/scripts/build_resume.py).

Run with the chapter venv:  .venv\\Scripts\\python.exe -m pytest tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "resume-tailor" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_resume as br  # noqa: E402

CHAPTER = Path(__file__).resolve().parents[1]
EXAMPLE_SPEC = CHAPTER / "examples" / "sample_resume_spec.md"

SPEC = """---
candidate: Test Candidate
target_role: Senior SDET
company: Acme
coverage_pct: 100
---

# Contact

Test Candidate
Senior SDET
test@example.com | +44 7700 900123 | Manchester, UK | linkedin.com/in/test

# Summary

Line one of the summary
wrapped onto a second line.

A second paragraph starts after a blank line.

# Core Skills

- Languages: Python, TypeScript
- Testing: Selenium WebDriver

# Experience

## Acme Corp | Senior SDET | Manchester, UK | Jan 2021 - Present

- Built 40 automated checks with Selenium WebDriver, cutting runtime 60%
- Mentored 3 engineers, raising coverage 25%

# JD Mapping

| Requirement | Priority | Coverage | Evidence | Where |
|---|---|---|---|---|
| Selenium WebDriver | must-have | Direct | 40 checks | Bullet 1 |
| Python | must-have | Direct | core language | Skills |
| k6 | nice-to-have | Gap | none | - |

# Keywords

| Keyword | In JD | In Master | In Tailored | Status |
|---|---|---|---|---|
| Selenium WebDriver | yes | yes | yes | ok |
| Python | yes | yes | yes | ok |
| k6 | yes | no | no | gap |

# Gap Analysis

| Gap | Severity | Mitigation |
|---|---|---|
| k6 | medium | learning target |
"""


def parse(text: str = SPEC) -> dict:
    return br.parse_spec(text)


# --------------------------------------------------------------------------- #
# contract violations
# --------------------------------------------------------------------------- #

def test_missing_frontmatter_is_rejected():
    with pytest.raises(br.SpecError, match="frontmatter"):
        br.parse_spec("# Summary\n\nHello\n")


def test_missing_candidate_is_rejected():
    with pytest.raises(br.SpecError, match="candidate"):
        br.parse_spec("---\ntarget_role: SDET\n---\n\n# Summary\n\nx\n")


def test_missing_required_section_is_rejected():
    text = SPEC.replace("# Core Skills", "# Skills I Like")
    with pytest.raises(br.SpecError, match="Core Skills"):
        br.parse_spec(text)


def test_wrong_table_header_is_rejected():
    text = SPEC.replace("| Requirement | Priority | Coverage | Evidence | Where |",
                        "| Req | Priority | Coverage | Evidence | Where |")
    with pytest.raises(br.SpecError, match="Requirement"):
        br.parse_spec(text)


def test_unknown_section_warns_but_does_not_fail():
    text = SPEC + "\n# Hobbies\n\n- Chess\n"
    spec = br.parse_spec(text)
    assert any("unknown section" in w for w in spec["warnings"])


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

def test_contact_and_headline_parse():
    spec = parse()
    assert spec["contact"]["name"] == "Test Candidate"
    assert spec["contact"]["title"] == "Senior SDET"
    assert spec["contact"]["details"] == [
        "test@example.com | +44 7700 900123 | Manchester, UK | linkedin.com/in/test"
    ]


def test_soft_wrapped_summary_is_one_paragraph():
    spec = parse()
    assert len(spec["summary"]) == 2
    assert spec["summary"][0] == "Line one of the summary wrapped onto a second line."
    assert spec["summary"][1] == "A second paragraph starts after a blank line."


def test_experience_heading_fields_and_dates():
    role = parse()["experience"][0]
    assert role["company"] == "Acme Corp"
    assert role["title"] == "Senior SDET"
    assert role["location"] == "Manchester, UK"
    assert role["dates"] == "Jan 2021 - Present"
    assert len(role["bullets"]) == 2


def test_missing_date_range_warns():
    text = SPEC.replace("Jan 2021 - Present", "")
    spec = br.parse_spec(text)
    assert any("no parseable date range" in w for w in spec["warnings"])


def test_company_written_as_title_warns():
    """Guard against '## Senior SDET | Acme Corp' - the order is Company | Title."""
    text = SPEC.replace("## Acme Corp | Senior SDET", "## Senior SDET | Acme Corp")
    spec = br.parse_spec(text)
    assert any("reads like a job title" in w for w in spec["warnings"])


def test_soft_wrapped_bullet_is_merged():
    text = SPEC.replace(
        "- Built 40 automated checks with Selenium WebDriver, cutting runtime 60%",
        "- Built 40 automated checks with Selenium WebDriver,\n  cutting runtime 60%",
    )
    bullets = br.parse_spec(text)["experience"][0]["bullets"]
    assert bullets[0] == "Built 40 automated checks with Selenium WebDriver, cutting runtime 60%"


def test_skills_split_into_category_and_items():
    skills = parse()["skills"]
    assert skills[0] == ("Languages", "Python, TypeScript")
    assert skills[1] == ("Testing", "Selenium WebDriver")


def test_bullets_in_summary_are_ignored_with_a_warning():
    text = SPEC.replace("Line one of the summary", "- Line one of the summary")
    spec = br.parse_spec(text)
    assert any("ignored" in w for w in spec["warnings"])


# --------------------------------------------------------------------------- #
# derived maths
# --------------------------------------------------------------------------- #

def test_coverage_weights_partial_at_half():
    mapping = [
        {"Priority": "must-have", "Coverage": "Direct"},
        {"Priority": "must-have", "Coverage": "Partial"},
        {"Priority": "nice-to-have", "Coverage": "Gap"},
    ]
    assert br.compute_coverage(mapping) == {
        "must": 2, "direct": 1, "partial": 1, "gap": 0, "pct": 75,
    }


def test_coverage_ignores_nice_to_haves():
    mapping = [
        {"Priority": "must-have", "Coverage": "Direct"},
        {"Priority": "nice-to-have", "Coverage": "Direct"},
    ]
    assert br.compute_coverage(mapping)["pct"] == 100


def test_keyword_matching_respects_word_boundaries():
    assert br._keyword_hits("Python and JavaScript", "Java") is False
    assert br._keyword_hits("Java 17 services", "Java") is True
    assert br._keyword_hits("we use GitHub Actions daily", "GitHub Actions") is True


def test_evidence_matching_tolerates_wording_differences():
    master = "Test automation engineer. Mentored 3 engineers and owned the test framework design."
    assert br._evidence_hits(master, "mentoring") is True
    assert br._evidence_hits(master, "test automation framework") is True
    assert br._evidence_hits("Mentored 3 engineers.", "test automation framework") is False
    assert br._evidence_hits(master, "Playwright") is False
    # short tokens stay strict so the fabrication guard is not weakened
    assert br._evidence_hits("load testing with JMeter", "k6") is False


def test_comments_are_not_treated_as_evidence():
    master = "Selenium only.\n<!-- No Playwright experience; k6 never used -->\n"
    stripped = br.strip_comments(master)
    assert br._evidence_hits(stripped, "Playwright") is False
    assert br._evidence_hits(stripped, "k6") is False


def test_bullet_audit_flags_quantification_and_verbs():
    spec = parse()
    rows = br.build_bullet_audit(spec, ["Selenium WebDriver", "Python"])
    assert rows[0]["Quantified"] == "yes"
    assert rows[0]["Starts With Verb"] == "yes"
    assert rows[0]["JD Keywords Hit"] == "Selenium WebDriver"
    assert rows[0]["Role"] == "Senior SDET - Acme Corp"


# --------------------------------------------------------------------------- #
# end-to-end rendering
# --------------------------------------------------------------------------- #

def test_end_to_end_render_produces_ats_safe_docx_and_audit_xlsx(tmp_path):
    from docx import Document
    import openpyxl

    spec_path = tmp_path / "resume_spec.md"
    spec_path.write_text(SPEC, encoding="utf-8")

    code = br.main([str(spec_path), "--chapter", str(CHAPTER), "--out", str(tmp_path)])
    assert code == 0

    doc = Document(str(tmp_path / "resume.docx"))
    assert len(doc.tables) == 0, "no tables may reach the resume body"
    assert len(doc.inline_shapes) == 0, "no images may reach the resume body"
    assert len(doc.sections) == 1, "single column only"
    styles = {p.style.name for p in doc.paragraphs}
    assert "List Bullet" in styles, "bullets must be real Word lists"
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "SUMMARY" in text and "CORE SKILLS" in text and "EXPERIENCE" in text
    # soft-wrapped summary must land as a single paragraph
    summary = [p.text for p in doc.paragraphs if p.text.startswith("Line one")][0]
    assert summary == "Line one of the summary wrapped onto a second line."

    wb = openpyxl.load_workbook(str(tmp_path / "resume_audit.xlsx"))
    assert wb.sheetnames == ["Master", "JD_Mapping", "Bullets", "Keywords", "Gap_Analysis"]
    assert all(ws.freeze_panes == "A2" for ws in wb.worksheets)


def test_example_fixture_renders_and_reports_the_gap(tmp_path, capsys):
    code = br.main([str(EXAMPLE_SPEC), "--chapter", str(CHAPTER), "--out", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 0, output
    assert "Coverage        : 94%" in output
    assert (tmp_path / "resume.docx").exists()
    assert (tmp_path / "resume_audit.xlsx").exists()


def test_check_only_writes_nothing(tmp_path, capsys):
    code = br.main([str(EXAMPLE_SPEC), "--chapter", str(CHAPTER), "--out", str(tmp_path), "--check-only"])
    assert code == 0
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

def test_claimed_direct_but_absent_from_resume_fails(tmp_path, capsys):
    text = (
        SPEC.replace("| k6 | nice-to-have | Gap | none | - |",
                     "| Playwright | must-have | Direct | claimed | Bullets |")
        .replace("| k6 | yes | no | no | gap |", "| Playwright | yes | no | no | ok |")
    )
    spec_path = tmp_path / "resume_spec.md"
    spec_path.write_text(text, encoding="utf-8")

    code = br.main([str(spec_path), "--chapter", str(CHAPTER), "--out", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 2
    assert "claimed 'Direct'" in output


def test_missing_email_fails_the_verification(tmp_path, capsys):
    text = SPEC.replace("test@example.com | +44 7700 900123 | Manchester, UK | linkedin.com/in/test",
                        "Manchester, UK | linkedin.com/in/test")
    spec_path = tmp_path / "resume_spec.md"
    spec_path.write_text(text, encoding="utf-8")

    code = br.main([str(spec_path), "--chapter", str(CHAPTER), "--out", str(tmp_path)])
    output = capsys.readouterr().out
    assert code == 2
    assert "email" in output


def test_lenient_page_estimate_is_reported():
    pages = br.estimate_pages(parse())
    assert 0.2 < pages < 2.0
