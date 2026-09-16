"""Minimal Jira Cloud REST client.

Fetches an issue by key and builds a plain-text digest for the LLM. Credentials
(URL/email/API token) are passed in per call and never stored or logged here.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import requests

from .logger import get_logger

log = get_logger()

# Jira keys: PROJECT-123 (letters/digits project, digits issue number).
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9_]{1,19}-\d{1,9})\b", re.IGNORECASE)

_FIELDS = (
    "summary,description,issuetype,status,priority,labels,components,"
    "creator,assignee,comment"
)

_AC_SECTION_RE = re.compile(
    r"^#{1,3}\s*acceptance\s*criteri[ao]", re.IGNORECASE | re.MULTILINE
)


class JiraError(Exception):
    """Base for user-facing Jira failures."""


class JiraAuthError(JiraError):
    """401/403 — bad URL, email, or API token."""


class JiraNotFoundError(JiraError):
    """404 — the issue key does not exist or is not visible."""


class JiraConnectionError(JiraError):
    """Network/timeout/server error."""


def parse_jira_key(text: str) -> str | None:
    """Extract the first Jira issue key from free text."""
    match = JIRA_KEY_RE.search(text or "")
    return match.group(1).upper() if match else None


def _issue_url(jira_url: str, issue_key: str) -> str:
    base = jira_url.rstrip("/")
    return f"{base}/rest/api/3/issue/{issue_key}"


def _auth_header(email: str, api_token: str) -> dict[str, str]:
    cred = base64.b64encode(f"{email}:{api_token}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {cred}"}


def _adf_to_text(node) -> str:
    """Convert an Atlassian Document Format node to plain text."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            text = node.get("text", "")
            if node.get("marks"):
                for mark in node["marks"]:
                    if mark.get("type") == "code":
                        text = f"`{text}`"
            return text
        if node_type == "hardBreak":
            return "\n"
        if node_type == "rule":
            return "\n---\n"
        if node_type == "codeBlock":
            return "\n```\n" + _flatten(node.get("content", [])) + "\n```\n"
        if node_type == "bulletList":
            parts = [_adf_to_text(c) for c in node.get("content", [])]
            return "\n" + "\n".join(f"- {p}" for p in parts if p) + "\n"
        if node_type == "orderedList":
            parts = [_adf_to_text(c) for c in node.get("content", [])]
            return "\n" + "\n".join(f"1. {p}" for p in parts if p) + "\n"
        if node_type == "listItem":
            return _flatten(node.get("content", []))
        if node_type == "table":
            rows = [_adf_to_text(c) for c in node.get("content", [])]
            return "\n" + "\n".join(f"| {r} |" for r in rows if r) + "\n"
        if node_type == "tableRow":
            return _flatten(node.get("content", []))
        if node_type == "tableCell":
            return "| " + _flatten(node.get("content", [])).strip()
        if node_type == "panel":
            return _flatten(node.get("content", []))
        if node_type == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            inner = _flatten(node.get("content", [])).strip()
            return f"\n{'#' * min(level, 6)} {inner}\n" if inner else ""
        # Generic containers (doc, paragraph, blockquote, ...)
        return _flatten(node.get("content", []))
    return ""


def _flatten(nodes) -> str:
    return "".join(_adf_to_text(n) for n in nodes or [])


def _description_to_text(description) -> str:
    """Description may be ADF (dict), legacy wiki (str), or None."""
    if description is None:
        return ""
    if isinstance(description, str):
        return description
    if isinstance(description, dict):
        return _flatten(description.get("content", [])).strip()
    return str(description)


def _comment_texts(comments: list) -> list[str]:
    out = []
    for comment in comments or []:
        body = comment.get("body")
        author = (comment.get("author") or {}).get("displayName", "unknown")
        text = _description_to_text(body)
        if text:
            out.append(f"{author}: {text}")
    return out


def _extract_acceptance_criteria(description_text: str) -> str:
    """Return text under an 'Acceptance Criteria' heading if present."""
    match = _AC_SECTION_RE.search(description_text)
    if not match:
        return ""
    return description_text[match.end():].strip()


def build_digest(issue: dict) -> str:
    """Turn a Jira issue JSON into a markdown digest for the LLM."""
    fields = issue.get("fields", {})

    def name(field_key: str) -> str:
        value = fields.get(field_key)
        if isinstance(value, dict):
            return value.get("name") or value.get("value") or value.get("displayName") or ""
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    names.append(
                        item.get("name") or item.get("value")
                        or item.get("displayName") or ""
                    )
                else:
                    names.append(str(item))
            return ", ".join(n for n in names if n)
        return str(value or "")

    summary = fields.get("summary") or "No summary"
    description_raw = _description_to_text(fields.get("description"))
    status = name("status")
    issuetype = name("issuetype")
    priority = name("priority")
    labels = ", ".join(fields.get("labels") or []) or "None"
    components = name("components") or "None"
    creator = name("creator")
    assignee = name("assignee") or "Unassigned"

    ac = _extract_acceptance_criteria(description_raw)
    comments = _comment_texts((fields.get("comment") or {}).get("comments", []))

    lines = [
        f"# Jira Issue: {issue.get('key', 'UNKNOWN')}",
        f"- Summary: {summary}",
        f"- Type: {issuetype}",
        f"- Status: {status}",
        f"- Priority: {priority}",
        f"- Labels: {labels}",
        f"- Components: {components}",
        f"- Creator: {creator}",
        f"- Assignee: {assignee}",
    ]

    if description_raw:
        if ac:
            lines.append("\n## Full description\n" + description_raw)
            lines.append("\n## Acceptance Criteria\n" + ac)
        else:
            lines.append("\n## Description\n" + description_raw)
    else:
        lines.append("\n## Description\nNo description provided.")

    if comments:
        lines.append("\n## Comments\n- " + "\n- ".join(comments))

    return "\n".join(lines)


def fetch_ticket(jira_url: str, email: str, api_token: str, issue_key: str,
                 timeout: int = 30) -> dict:
    """Fetch a Jira issue and return its raw JSON (key + fields)."""
    url = _issue_url(jira_url, issue_key)
    headers = {
        "Accept": "application/json",
        **_auth_header(email, api_token),
    }
    params = {"fields": _FIELDS}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    except requests.exceptions.Timeout:
        log.info("jira fetch timed out for %s", issue_key)
        raise JiraConnectionError(
            f"Jira request timed out after {timeout}s. Check that the URL is reachable."
        ) from None
    except requests.exceptions.RequestException as exc:
        log.info("jira fetch network error for %s: %s", issue_key, type(exc).__name__)
        raise JiraConnectionError(
            "Could not reach Jira. Check the Jira URL in Settings and your network."
        ) from None

    if resp.status_code in (401, 403):
        log.info("jira auth failed for %s (HTTP %s)", issue_key, resp.status_code)
        raise JiraAuthError(
            "Jira authentication failed (HTTP 401/403). Check the email and API "
            "token in Settings."
        )
    if resp.status_code == 404:
        log.info("jira issue not found: %s", issue_key)
        raise JiraNotFoundError(
            f"Jira issue '{issue_key}' was not found, or your account cannot see it."
        )
    if resp.status_code >= 400:
        log.info("jira error for %s (HTTP %s)", issue_key, resp.status_code)
        raise JiraConnectionError(
            f"Jira returned an error (HTTP {resp.status_code}). "
            f"Response: {resp.text[:200]}"
        )

    return resp.json()
