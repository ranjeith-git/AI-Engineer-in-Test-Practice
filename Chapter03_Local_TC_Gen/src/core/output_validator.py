"""Output validator.

Checks LLM output against the template's structural contract (column headers,
Test ID numbering, allowed Priority values) WITHOUT hardcoding any of those
values. If the template does not state a rule, the validator does not enforce
it — the template is the only authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .template_loader import TemplateFile

_HEADER_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_TEST_ID_RE = re.compile(r"^\s*TC-\d+\s*$", re.IGNORECASE)


@dataclass
class ValidationResult:
    valid: bool
    reasons: list[str] = field(default_factory=list)


def _parse_table_blocks(text: str) -> list[list[list[str]]]:
    """Return tables as lists of rows (each row a list of cleaned cells).

    A table starts at a header line and ends at the first blank/non-pipe line
    after its separator row. Handles preamble text before the table.
    """
    lines = text.splitlines()
    tables: list[list[list[str]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _HEADER_ROW_RE.match(line):
            i += 1
            continue
        # Require a separator row right after the candidate header.
        if i + 1 >= len(lines) or not _SEPARATOR_RE.match(lines[i + 1]):
            i += 1
            continue
        table: list[list[str]] = []
        j = i
        while j < len(lines) and lines[j].strip().startswith("|"):
            # Skip the separator row (e.g. |---|---|) — it is not a data row.
            if not _SEPARATOR_RE.match(lines[j]):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                table.append([c for c in cells if c])
            j += 1
        if len(table) >= 2:  # header + at least one data row
            tables.append(table)
        i = j
    return tables


def _priorities_from_template(template: TemplateFile) -> set[str]:
    """Extract allowed Priority values from the template's own rules.

    Looks for lines containing 'priority' and 'High/Medium/Low'-style tokens.
    If nothing is found the validator does not constrain Priority.
    """
    allowed: set[str] = set()
    for line in template.raw_text.splitlines():
        if "priority" not in line.lower():
            continue
        for token in re.findall(r"\b(High|Medium|Low)\b", line, flags=re.IGNORECASE):
            allowed.add(token.title())
    return allowed


def validate(output_text: str, template: TemplateFile) -> ValidationResult:
    """Validate output against the template contract."""
    reasons: list[str] = []
    text = (output_text or "").strip()
    if not text:
        return ValidationResult(False, ["LLM returned empty output."])

    # LLMs often wrap their answer in a ``` code fence. A fenced table is
    # still a valid table — strip balanced leading/trailing fence lines.
    fenced = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    expected_headers = [h.strip().lower() for h in template.expected_headers]
    if not expected_headers:
        # Template defines no table — we cannot validate structure. Treat as
        # pass-through; the caller decides based on template content.
        return ValidationResult(True, [])

    tables = _parse_table_blocks(text)
    if not tables:
        reasons.append(
            "Output contains no markdown table. Expected a table with columns: "
            + template.header_text()
        )
        return ValidationResult(False, reasons)

    # Check the FIRST table (the template expects a single generated table).
    first_row, *rest_rows = tables[0]

    # Headerless-table accommodation: small local models sometimes copy the
    # template's EXAMPLE ROW shape (data row then separator) and omit the
    # header row. In that case the parser mislabeled the first DATA row as a
    # header. If the first row is not a header, substitute the template's
    # declared headers and treat every parsed row as data.
    first_row_lc = [c.strip().lower() for c in first_row]
    looks_like_header = any(h in first_row_lc for h in ("test id", "id"))
    if not looks_like_header:
        header_row = template.expected_headers
        # The first "row" the parser kept is actually the first data row, and
        # it skipped the separator after it. So ALL parsed rows are data.
        data_rows = [first_row, *rest_rows]
    else:
        header_row = first_row
        data_rows = rest_rows

    actual_headers = [h.strip().lower() for h in header_row]

    missing = [h for h in expected_headers if h not in actual_headers]
    if missing:
        reasons.append(
            "Output table is missing required column(s): "
            + ", ".join(missing)
            + f". Expected: {template.header_text()}"
        )

    # Column ORDER and unknown-column checks (template-driven, no hardcoding):
    # the expected header sequence is the contract, so the actual headers must
    # appear in that same relative order, and no extra/unknown columns may be
    # introduced beyond the template's set.
    expected_lc = expected_headers
    in_expected = [h for h in actual_headers if h in expected_lc]
    if in_expected != expected_lc:
        reasons.append(
            "Output table column order does not match the template. "
            f"Expected: {template.header_text()}. Got: "
            + " | ".join(actual_headers)
        )
    extras = [h for h in actual_headers if h not in expected_lc]
    if extras:
        reasons.append(
            "Output table has column(s) not in the template: "
            + ", ".join(extras)
            + f". Expected only: {template.header_text()}"
        )

    if not data_rows:
        reasons.append("Output table has no data rows.")

    # Column position of Test ID / Priority in the TEMPLATE (source of truth).
    try:
        id_col = actual_headers.index(
            next(h for h in ("test id", "id") if h in actual_headers)
        )
    except StopIteration:
        id_col = None
    pri_col = None
    for idx, h in enumerate(actual_headers):
        if h == "priority":
            pri_col = idx
            break

    if id_col is not None:
        bad_ids = [
            row[id_col] for row in data_rows
            if id_col < len(row) and not _TEST_ID_RE.match(row[id_col])
        ]
        # Allow numeric ids too (TC-1, 1) only if the template doesn't say TC-XXX.
        numeric_ok = "TC-" not in template.raw_text
        if bad_ids:
            if not (numeric_ok and all(bad.replace(" ", "").isdigit() for bad in bad_ids)):
                reasons.append(
                    "Test ID values do not match the template numbering "
                    f"(expected format from template, e.g. TC-001). Found: {bad_ids[:5]}"
                )

    allowed_priorities = _priorities_from_template(template)
    if pri_col is not None and allowed_priorities:
        bad_pri = [
            row[pri_col] for row in data_rows
            if pri_col < len(row) and row[pri_col].strip() not in allowed_priorities
        ]
        if bad_pri:
            reasons.append(
                "Priority values are not in the template's allowed set "
                f"({sorted(allowed_priorities)}). Found: {bad_pri[:5]}"
            )

    return ValidationResult(valid=not reasons, reasons=reasons)
