"""Parse a generated markdown table into structured test-case records.

Framework-agnostic: this module knows nothing about Streamlit. The chat page
turns these records into cards. It accepts the shapes small local models
actually emit — a fenced table, escaped pipes, or data rows with no header row —
so the view only falls back to raw markdown when the output is genuinely not a
table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A whole answer wrapped in ```markdown ... ``` fences.
_FENCE_RE = re.compile(r"^\s*```(?:markdown|md)?\s*\n(.*?)\n\s*```\s*$", re.DOTALL)
_ROW_RE = re.compile(r"^\s*\|.+\|\s*$")
_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
# Cells that label the row rather than describe the test.
_META_HEADERS = {"test id", "id", "testid", "description", "priority"}
_STEP_HEADERS = {"steps", "step", "test steps"}
# "1. text", "2) text" — the numbering in the template's Steps column.
_STEP_MARKER_RE = re.compile(r"(?:^|\s)(\d{1,2})[.)]\s+")


@dataclass
class TestCase:
    """One generated test case, keyed by the template's column names."""

    values: dict[str, str] = field(default_factory=dict)

    def get(self, *names: str) -> str:
        """Value for the first matching column name (case-insensitive)."""
        wanted = {n.strip().lower() for n in names}
        for key, value in self.values.items():
            if key.strip().lower() in wanted:
                return value
        return ""

    def text(self) -> str:
        """All cell text, for search/filtering."""
        return " ".join(self.values.values())


@dataclass
class ParsedTable:
    headers: list[str] = field(default_factory=list)
    cases: list[TestCase] = field(default_factory=list)
    preamble: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.cases)


def split_steps(value: str) -> list[str]:
    """Split a Steps cell into individual steps.

    Handles "1. a 2. b", "1) a\\n2) b" and a plain sentence (single step).
    """
    text = (value or "").strip()
    if not text:
        return []
    parts = _STEP_MARKER_RE.split(text)
    if len(parts) < 3:
        return [text]
    steps = [parts[i].strip() for i in range(2, len(parts), 2)]
    lead = parts[0].strip()
    if lead:
        steps.insert(0, lead)
    return [s for s in steps if s]


def split_cells(line: str) -> list[str]:
    """Split one table row into cells, honouring escaped pipes."""
    inner = line.strip().strip("|")
    return [c.replace("\\|", "|").strip() for c in _UNESCAPED_PIPE_RE.split(inner)]


def _looks_like_header(cells: list[str]) -> bool:
    return any(c.strip().lower() in ("test id", "id", "testid") for c in cells)


def parse_test_cases(
    text: str,
    expected_headers: list[str] | None = None,
) -> ParsedTable:
    """Parse the first markdown table in `text` into test-case records.

    `expected_headers` is the template's column contract; when it lines up with
    the table's column count it supplies the labels, so a model that renames
    "Pre-conditions" to "Preconditions" still gets the template's label.
    """
    raw = (text or "").strip()
    if not raw:
        return ParsedTable()

    fenced = _FENCE_RE.match(raw)
    if fenced:
        raw = fenced.group(1).strip()

    lines = raw.splitlines()
    expected = [h.strip() for h in (expected_headers or []) if h.strip()]

    start = None
    for i, line in enumerate(lines):
        if _ROW_RE.match(line) and i + 1 < len(lines) and _SEPARATOR_RE.match(lines[i + 1]):
            start = i
            break
    if start is None:
        return ParsedTable(preamble=raw)

    header_cells = split_cells(lines[start])

    body: list[list[str]] = []
    i = start + 2  # skip header + separator
    while i < len(lines) and lines[i].strip().startswith("|"):
        if not _SEPARATOR_RE.match(lines[i]):
            cells = split_cells(lines[i])
            if any(cells):
                body.append(cells)
        i += 1

    preamble = "\n".join(lines[:start]).strip()

    if _looks_like_header(header_cells):
        labels, rows = header_cells, body
    else:
        # The model copied the template's example data row and dropped the
        # header: every parsed row is data, labelled from the template.
        labels = expected or [f"Column {n}" for n in range(1, len(header_cells) + 1)]
        rows = [header_cells, *body]

    if expected and len(expected) == len(labels):
        labels = expected

    cases = [
        TestCase(values={
            label: (row[idx].strip() if idx < len(row) else "")
            for idx, label in enumerate(labels)
        })
        for row in rows
    ]
    return ParsedTable(headers=labels, cases=cases, preamble=preamble)


def field_order(headers: list[str]) -> list[str]:
    """Columns to show as card fields: everything but ID/description/priority,
    with the Steps column last so it can own the full card width."""
    steps = next(
        (h for h in headers if h.strip().lower() in _STEP_HEADERS), None
    )
    rest = [
        h for h in headers
        if h.strip().lower() not in _META_HEADERS and h != steps
    ]
    return rest + ([steps] if steps else [])


def is_step_column(header: str) -> bool:
    return header.strip().lower() in _STEP_HEADERS
