#!/usr/bin/env python
"""Review local changes, then commit and push them - only after you confirm.

    python scripts/push-review.py                     # everything that changed
    python scripts/push-review.py Chapter05_Notes     # only that path
    python scripts/push-review.py -m "Add notes"
    python scripts/push-review.py --dry-run           # show the plan, change nothing
    python scripts/push-review.py --no-push           # commit locally, don't push

Nothing is staged, committed or pushed until you type PUSH at the prompt. A bare
Enter cancels. Stdlib only, so any Python 3 on PATH can run it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

CONFIRM_WORD = "PUSH"
CO_AUTHOR = "Co-authored-by: CommandCodeBot <noreply@commandcode.ai>"
MAX_LISTED = 20

# A public repo: catch credential-shaped files and strings before they leave the machine.
SECRET_PATH_RE = re.compile(
    r"(^|/)(\.env|\.env\.[^/]+|id_rsa|id_ed25519|.*\.pem|.*\.key|.*\.pfx|.*\.p12"
    r"|credentials.*\.json|\.npmrc|\.pypirc|secrets?\.(ya?ml|json|txt))$",
    re.IGNORECASE,
)
SECRET_PATH_OK_RE = re.compile(r"\.env\.(example|sample|template)$", re.IGNORECASE)
SECRET_CONTENT_RES = (
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Groq key", re.compile(r"\bgsk_[A-Za-z0-9]{30,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
)


def out(text: str = "") -> None:
    print(text)


def git(args: list[str], repo: Path, check: bool = True) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        sys.stderr.write(f"ERROR: git {' '.join(args)} failed\n{proc.stdout}{proc.stderr}")
        raise SystemExit(1)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        sys.stderr.write("ERROR: not inside a git repository\n")
        raise SystemExit(1)
    return Path(proc.stdout.strip())


def parse_status(porcelain: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((code, path.strip().strip('"')))
    return entries


def display_status(code: str) -> str:
    if code == "??":
        return "A"
    for char in code:
        if char not in " !":
            return char
    return "?"


def is_new(code: str) -> bool:
    return code == "??" or "A" in code


def count_lines(repo: Path, rel_path: str) -> int | None:
    path = repo / rel_path
    if not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:8000]:
        return None
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def scan_secrets(repo: Path, entries: list[tuple[str, str]], touch_only_untracked: bool) -> list[str]:
    findings: list[str] = []
    for code, path in entries:
        if SECRET_PATH_RE.search(path) and not SECRET_PATH_OK_RE.search(path):
            findings.append(f"{path} - filename looks like a credential store")
            continue
        if touch_only_untracked and not is_new(code):
            continue
        full = repo / path
        if not full.is_file() or full.stat().st_size > 2_000_000:
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_CONTENT_RES:
            if pattern.search(text):
                findings.append(f"{path} - looks like a live {label}")
                break
    return findings


def default_message(entries: list[tuple[str, str]]) -> str:
    tops: list[str] = []
    for _, path in entries:
        top = path.split("/")[0]
        if top not in tops:
            tops.append(top)
    if len(tops) == 1:
        verb = "Add" if all(is_new(c) for c, _ in entries) else "Update"
        return f"{verb} {tops[0]}"
    return f"Update {len(tops)} areas"


def summarize(repo: Path, entries: list[tuple[str, str]]) -> None:
    additions = deletions = 0
    _, numstat = git(["diff", "HEAD", "--numstat"], repo, check=False)
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            additions += int(parts[0])
            deletions += int(parts[1])

    for code, path in entries:
        if is_new(code):
            counted = count_lines(repo, path)
            if counted is not None:
                additions += counted

    out("  Changes ready to push:")
    out("")
    listed = sorted(entries, key=lambda e: e[1])[:MAX_LISTED]
    for code, path in listed:
        counted = count_lines(repo, path) if is_new(code) else None
        suffix = "" if counted is None else f"  ({counted} line{'' if counted == 1 else 's'})"
        out(f"    {display_status(code)}  {path}{suffix}")
    if len(entries) > MAX_LISTED:
        out(f"    ... and {len(entries) - MAX_LISTED} more")

    if len(entries) > MAX_LISTED:
        out("")
        out("  By folder:")
        groups: dict[str, list[str]] = {}
        for code, path in entries:
            groups.setdefault(path.split("/")[0], []).append(code)
        for name in sorted(groups):
            codes = groups[name]
            new_count = sum(1 for c in codes if is_new(c))
            out(f"    {name}/  - {len(codes)} file(s), {new_count} new")

    out("")
    out(f"  {len(entries)} path(s) changed, +{additions:,} / -{deletions:,} lines")


def to_web_url(remote: str) -> str:
    remote = remote.strip()
    match = re.match(r"git@([^:]+):(.+?)(?:\.git)?$", remote)
    if match:
        return f"https://{match.group(1)}/{match.group(2)}"
    return re.sub(r"\.git$", "", remote)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Review, confirm, then commit and push.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", help="limit the push to these paths")
    parser.add_argument("-m", "--message", help="commit message (prompted if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    parser.add_argument("--no-push", action="store_true", help="commit but do not push")
    parser.add_argument("--co-author", action="store_true",
                        help="append the CommandCodeBot co-author trailer")
    parser.add_argument("--allow-secrets", action="store_true",
                        help="proceed even though the secret scan flagged something")
    args = parser.parse_args(argv)

    repo = repo_root()

    # Rev-parse fails on an unborn branch (no commits yet), so ask symbolic-ref instead.
    git_dir_code, git_dir_out = git(["rev-parse", "--git-dir"], repo, check=False)
    git_dir = Path(git_dir_out.strip()) if git_dir_code == 0 and git_dir_out.strip() else Path(".git")
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    for probe in ("MERGE_HEAD", "REBASE_HEAD", "rebase-merge", "CHERRY_PICK_HEAD"):
        if (git_dir / probe).exists():
            out(f"Refusing to run: a {probe.replace('_HEAD', '').replace('-', ' ').lower()} is in progress.")
            out("Finish or abort it first (git status will explain the state).")
            return 1

    branch_code, branch_out = git(["symbolic-ref", "--short", "HEAD"], repo, check=False)
    if branch_code != 0:
        out("Refusing to run: HEAD is detached. Check out a branch first.")
        return 1
    branch = branch_out.strip()

    remote = git(["remote", "get-url", "origin"], repo, check=False)[1].strip()

    status_args = ["status", "--porcelain", "-uall"]
    if args.paths:
        status_args += ["--", *args.paths]
    entries = parse_status(git(status_args, repo)[1])

    if not entries:
        scope = f" under {' '.join(args.paths)}" if args.paths else ""
        out(f"Nothing to push{scope} - working tree is clean.")
        return 0

    out()
    summarize(repo, entries)

    findings = scan_secrets(repo, entries, touch_only_untracked=False)
    if findings:
        out("")
        out("  SECRET CHECK FAILED - refusing to push:")
        for item in findings:
            out(f"    ! {item}")
        if not args.allow_secrets:
            out("")
            out("  Move these out of the repo or add them to .gitignore, then re-run.")
            out("  Override with --allow-secrets only if you are certain they are placeholders.")
            return 1
        out("  --allow-secrets given, continuing anyway.")

    if args.dry_run:
        out("")
        out("  Dry run: nothing was staged, committed or pushed.")
        return 0

    out("")
    if args.message:
        message = args.message
        out(f"  Commit message: {message}")
    else:
        suggestion = default_message(entries)
        try:
            typed = input(f"  Commit message [{suggestion}]: ").strip()
        except EOFError:
            out("  Input closed - cancelled.")
            return 1
        message = typed or suggestion

    out("")
    out("  " + "-" * 66)
    out(f"  Branch : {branch}" + (f"  ->  {remote}" if remote else ""))
    if args.no_push:
        out("  Action : commit only (--no-push)")
    else:
        out(f"  Action : commit and push {len(entries)} path(s) to origin/{branch}")
    out("  " + "-" * 66)
    try:
        answer = input(f"  Type {CONFIRM_WORD} to confirm (anything else cancels): ").strip()
    except EOFError:
        answer = ""
    if answer.upper() != CONFIRM_WORD:
        out("  Cancelled - nothing was changed.")
        return 1

    add_args = ["add", "-A"]
    if args.paths:
        add_args += ["--", *args.paths]
    git(add_args, repo)

    body = message if not args.co_author else f"{message}\n\n{CO_AUTHOR}"
    proc = subprocess.run(
        ["git", "commit", "-F", "-", *(["--"] + args.paths if args.paths else [])],
        cwd=str(repo), input=body, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        out("  Commit failed - nothing was pushed.")
        return 1
    first_line = proc.stdout.splitlines()[0] if proc.stdout else "committed"
    out(f"  {first_line.strip()}")

    if args.no_push:
        out("  Not pushed (--no-push).")
        return 0

    has_upstream = git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo, check=False)[0] == 0
    push_args = ["push"] if has_upstream else ["push", "-u", "origin", branch]
    proc = subprocess.run(
        ["git", *push_args], cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout + proc.stderr)
        out("  Push FAILED - the commit is local only. Fix the error and run: git push")
        return 1

    out(f"  Pushed to origin/{branch}")
    if remote:
        out(f"  {to_web_url(remote)}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best effort on legacy consoles
        pass
    sys.exit(main())
