"""Runtime template loading.

The template file (templates/test cases creator.md) is the single source of
truth for the output format. It is read fresh on every generation so edits
apply on the next run with no code change. If the file is missing, unreadable,
or empty the app fails gracefully — there is NO hardcoded fallback format.

We also do a light parse of the first markdown table's header row so the
output validator can programmatically check that generated columns match the
template without dictating any format ourselves.

`prompt_text()` additionally strips the template's example scaffolding (an
EXAMPLE ROW and a "[PASTE REQUIREMENTS HERE]" placeholder line) before the
template is injected into the LLM prompt — those are format references for a
human author, and the model copies them instead of following the real rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TemplateFile:
    path: Path
    raw_text: str
    ok: bool = True
    error: str = ""
    expected_headers: list[str] = field(default_factory=list)

    def header_text(self) -> str:
        return " | ".join(self.expected_headers)

    def prompt_text(self) -> str:
        """Template content safe to inject into the LLM prompt.

        Strips the human-facing example scaffolding (an EXAMPLE ROW line and a
        trailing 'REQUIREMENTS/JIRA ID : [PASTE REQUIREMENTS HERE]' placeholder)
        so the model cannot copy the example content or echo the placeholder.
        `raw_text` is left untouched — the validator still parses the real file.
        """
        text = self.raw_text
        # Drop the trailing "REQUIREMENTS/JIRA ID : [PASTE REQUIREMENTS HERE]"
        # placeholder line (and any trailing blank lines around it).
        text = re.sub(
            r"(?im)^\s*requirements\s*/\s*jira\s+id\s*:.*\[.*paste.*requirements.*\].*\s*$",
            "",
            text,
        )
        # Drop the EXAMPLE ROW line entirely.
        text = re.sub(r"(?im)^\s*example\s+row.*$", "", text)
        # Collapse the 3+ blank lines the removals leave behind.
        return re.sub(r"\n{3,}", "\n\n", text).strip()


# e.g. '2.Use these exact column headers: | Test ID | Description | ... | Priority |'
_INLINE_HEADERS_RE = re.compile(
    r"(?:column headers?|columns?)\s*[:=]\s*(\|.+\|)", re.IGNORECASE
)


def _cells_from_pipe_text(text: str) -> list[str]:
    cells = [c.strip() for c in text.strip().strip("|").split("|")]
    return [c for c in cells if c]


def _extract_headers(raw_text: str) -> list[str]:
    """Pull the header cells from the template.

    Two supported shapes, in priority order:
    1. An actual markdown table (header row followed by a --- separator row).
    2. An inline rule like "Use these exact column headers: | A | B | C |",
       which this template format uses as the column contract.
    """
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        if i + 1 >= len(lines):
            break
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Separator row looks like | --- | :---: | etc.
        next_stripped = lines[i + 1].strip()
        if re.fullmatch(r"\|[\s:|-]+\|", next_stripped):
            return _cells_from_pipe_text(stripped)

    match = _INLINE_HEADERS_RE.search(raw_text)
    if match:
        cells = _cells_from_pipe_text(match.group(1))
        if cells:
            return cells

    return []


def load_template(path: str | Path) -> TemplateFile:
    """Read and lightly parse the template file."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return TemplateFile(
            path=p, raw_text="", ok=False,
            error=f"Template file not found: {p}. Place your 'test cases creator' "
                  f"template at this path and try again.",
        )
    except OSError as exc:
        return TemplateFile(
            path=p, raw_text="", ok=False,
            error=f"Template file could not be read: {exc}",
        )

    if not raw.strip():
        return TemplateFile(
            path=p, raw_text="", ok=False,
            error=f"Template file is empty: {p}. Add your test-case format rules "
                  f"and try again.",
        )

    return TemplateFile(
        path=p,
        raw_text=raw,
        ok=True,
        expected_headers=_extract_headers(raw),
    )
