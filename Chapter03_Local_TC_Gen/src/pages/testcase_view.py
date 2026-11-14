"""Render generated test cases as scannable cards instead of a raw table.

The chat page calls `render_test_cases()` for every stored assistant message, so
a response looks identical on its first render and after any rerun. It returns
False when the text holds no parseable table, letting the caller fall back to
plain markdown rather than dropping the response.

Every value is HTML-escaped before it reaches the browser, and state is never
carried by colour alone — each priority shows its name in the badge.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from core.testcase_parser import (  # noqa: E402
    ParsedTable,
    TestCase,
    field_order,
    is_step_column,
    parse_test_cases,
    split_steps,
)

# Priority accent. Colour is a cue, never the message — the badge always spells
# the priority out.
_ACCENTS = {"high": "#e5484d", "medium": "#d9820a", "low": "#0f9d8f"}
_NEUTRAL_ACCENT = "#6b7280"
_MIN_CASES_FOR_FILTERS = 4
_PRIORITY_ORDER = ("High", "Medium", "Low")

_STYLES = """
<style>
.tc-stats { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 10px; }
.tc-stat {
  display:inline-flex; align-items:center; gap:7px; padding:4px 11px;
  border-radius:999px; font-size:0.74rem; font-weight:600; letter-spacing:0.01em;
  color:var(--text-color); background:rgba(128,128,128,0.08);
  background:color-mix(in srgb, var(--text-color) 7%, transparent);
  border:1px solid rgba(128,128,128,0.22);
  border:1px solid color-mix(in srgb, var(--text-color) 15%, transparent);
}
.tc-dot { width:8px; height:8px; border-radius:50%; flex:none; }
.tc-card {
  --tc-accent:#6b7280;
  border:1px solid rgba(128,128,128,0.22);
  border:1px solid color-mix(in srgb, var(--text-color) 14%, transparent);
  border-radius:12px; overflow:hidden; margin-bottom:14px;
  background:rgba(128,128,128,0.05);
  background:color-mix(in srgb, var(--secondary-background-color) 92%, var(--text-color) 8%);
}
.tc-banner {
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  padding:10px 14px 10px 12px; border-left:4px solid var(--tc-accent);
  border-bottom:1px solid rgba(128,128,128,0.18);
  border-bottom:1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
  background:rgba(128,128,128,0.06);
  background:color-mix(in srgb, var(--tc-accent) 7%, transparent);
}
.tc-id {
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:0.72rem; font-weight:700; letter-spacing:0.04em; white-space:nowrap;
  padding:2px 8px; border-radius:6px; color:var(--tc-accent);
  background:rgba(128,128,128,0.14);
  background:color-mix(in srgb, var(--tc-accent) 15%, transparent);
}
.tc-title { flex:1 1 240px; font-size:0.95rem; font-weight:600; line-height:1.35; }
.tc-badge {
  font-size:0.68rem; font-weight:700; letter-spacing:0.05em; text-transform:uppercase;
  white-space:nowrap; padding:3px 10px; border-radius:999px; color:var(--tc-accent);
  background:rgba(128,128,128,0.14);
  background:color-mix(in srgb, var(--tc-accent) 15%, transparent);
}
.tc-body {
  display:grid; grid-template-columns:1fr 1fr; gap:14px 18px; padding:14px 14px 15px;
}
.tc-field--wide { grid-column:1 / -1; }
.tc-label {
  font-size:0.63rem; font-weight:700; letter-spacing:0.09em; text-transform:uppercase;
  opacity:0.58; margin-bottom:5px;
}
.tc-value { font-size:0.88rem; line-height:1.55; white-space:pre-wrap; overflow-wrap:anywhere; }
.tc-steps { margin:0; padding-left:1.15rem; font-size:0.88rem; line-height:1.55; }
.tc-steps li { margin-bottom:5px; padding-left:2px; }
.tc-steps li:last-child { margin-bottom:0; }
@media (max-width:640px) { .tc-body { grid-template-columns:1fr; } }
</style>
"""


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _accent(priority: str) -> str:
    return _ACCENTS.get((priority or "").strip().lower(), _NEUTRAL_ACCENT)


def _priority_counts(table: ParsedTable) -> list[tuple[str, int]]:
    """Priority buckets in template order, then anything unexpected."""
    counts: dict[str, int] = {}
    for case in table.cases:
        priority = case.get("Priority") or "Unspecified"
        counts[priority] = counts.get(priority, 0) + 1
    ordered = [(p, counts[p]) for p in _PRIORITY_ORDER if p in counts]
    ordered += [(p, n) for p, n in counts.items() if p not in _PRIORITY_ORDER]
    return ordered


def _stats_html(table: ParsedTable) -> str:
    total = len(table.cases)
    pills = [
        f'<span class="tc-stat">{total} test case{"s" if total != 1 else ""}</span>'
    ]
    for priority, count in _priority_counts(table):
        pills.append(
            f'<span class="tc-stat">'
            f'<span class="tc-dot" style="background:{_accent(priority)}"></span>'
            f'{_esc(priority)} · {count}</span>'
        )
    return f'<div class="tc-stats">{"".join(pills)}</div>'


def _field_html(case: TestCase, header: str) -> str:
    wide = " tc-field--wide" if is_step_column(header) else ""
    raw = case.get(header)
    if is_step_column(header):
        steps = split_steps(raw)
        if len(steps) > 1:
            items = "".join(f"<li>{_esc(s)}</li>" for s in steps)
            body = f'<ol class="tc-steps">{items}</ol>'
        else:
            body = f'<div class="tc-value">{_esc(raw) or "—"}</div>'
    else:
        body = f'<div class="tc-value">{_esc(raw) or "—"}</div>'
    return (
        f'<div class="tc-field{wide}">'
        f'<div class="tc-label">{_esc(header)}</div>{body}</div>'
    )


def _card_html(case: TestCase, headers: list[str]) -> str:
    priority = case.get("Priority")
    test_id = case.get("Test ID", "ID") or "Test case"
    title = case.get("Description") or "Untitled test case"
    fields = "".join(_field_html(case, h) for h in field_order(headers))
    badge = (
        f'<span class="tc-badge">{_esc(priority)}</span>' if priority else ""
    )
    return (
        f'<article class="tc-card" style="--tc-accent:{_accent(priority)}">'
        f'<header class="tc-banner">'
        f'<span class="tc-id">{_esc(test_id)}</span>'
        f'<span class="tc-title">{_esc(title)}</span>'
        f"{badge}</header>"
        f'<div class="tc-body">{fields}</div>'
        f"</article>"
    )


def _filtered(table: ParsedTable, key: str) -> list[TestCase]:
    """Draw the filter controls and return the cases the user asked to see."""
    if len(table.cases) < _MIN_CASES_FOR_FILTERS:
        return table.cases

    priorities = [p for p, _ in _priority_counts(table)]
    options = ["All", *priorities]
    search_col, priority_col = st.columns([3, 2])
    with search_col:
        query = st.text_input(
            "Filter test cases",
            key=f"{key}_query",
            placeholder="Search description, steps, expected result...",
        )
    with priority_col:
        choice = st.segmented_control(
            "Priority",
            options=options,
            default="All",
            key=f"{key}_priority",
        )

    rows = table.cases
    if query and query.strip():
        needle = query.strip().lower()
        rows = [c for c in rows if needle in c.text().lower()]
    if choice and choice != "All":
        rows = [c for c in rows if (c.get("Priority") or "Unspecified") == choice]

    if len(rows) != len(table.cases):
        st.caption(f"Showing {len(rows)} of {len(table.cases)} test cases.")
    return rows


def render_test_cases(
    text: str,
    expected_headers: list[str] | None = None,
    key: str = "tc",
) -> bool:
    """Render `text` as test-case cards. False when it has no parseable table."""
    table = parse_test_cases(text, expected_headers)
    if not table.ok:
        return False

    st.html(_STYLES)
    if table.preamble:
        st.caption(table.preamble)
    st.html(_stats_html(table))

    cases = _filtered(table, key)
    if not cases:
        st.info("No test cases match the current filter.")
        return True

    st.html("".join(_card_html(case, table.headers) for case in cases))
    return True
