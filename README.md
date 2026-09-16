# AI Testing

This project is currently a placeholder. Add a description of the project here once it has content.

AI powered Testing for all Testing activities

Here we are going explore:

LLMs
MCPs
Langchain
Langflow
ATAN
RAG
much more testing activities an be achived by Agents

---

## Pushing changes to GitHub

This repo is connected to
[github.com/ranjeith-git/AI-Engineer-in-Test-Practice](https://github.com/ranjeith-git/AI-Engineer-in-Test-Practice)
as the `origin` remote. Credentials are handled by Git Credential Manager (`credential.helper=manager`),
so VS Code and the terminal can push over HTTPS without re-entering anything.

**The repo is public, and nothing is pushed automatically.** Every push goes through a
confirmation step you have to type yourself.

### From VS Code (recommended)

1. Press `Ctrl+Shift+P` and choose **Tasks: Run Task** (or `Ctrl+Shift+B` for the default task).
2. Pick **Git: Review & Push**.
3. The terminal panel opens listing every file that would go up, with line counts and totals.
4. Type a commit message, or press `Enter` to accept the suggested one.
5. Type `PUSH` and press `Enter`. **Anything else cancels** — a bare Enter changes nothing.
6. On success it prints the commit line, `Pushed to origin/<branch>`, and the GitHub URL.

Run **Git: Review & Push (dry run)** to preview without touching anything, and **Git: Status**
for a short status plus how far ahead of `origin` you are.

### From the terminal

```powershell
# preview only - changes nothing
py -3 scripts/push-review.py --dry-run

# review, confirm, then commit and push (type PUSH at the prompt)
py -3 scripts/push-review.py

# push only the chapter you just wrote, leaving everything else alone
py -3 scripts/push-review.py Chapter05_Your_New_Chapter

# commit locally but do not push
py -3 scripts/push-review.py --no-push

# append the CommandCodeBot co-author trailer to the commit
py -3 scripts/push-review.py --co-author
```

### What it refuses to do

- **Nothing to push** — exits cleanly when the working tree is clean.
- **Secret files** — refuses when a path looks like a credential store (`.env`, `*.pem`, `*.key`,
  `id_rsa`, `credentials*.json`, …) or a file contains live-looking key material. `.env.example`
  is explicitly allowed. Override only with `--allow-secrets`.
- **Mid-operation** — refuses if a merge, rebase or cherry-pick is in progress.
- **Detached HEAD** — refuses; check out a branch first.

Exit code is `0` on success and `1` on cancel or refusal, so it is safe to chain in scripts.

### Why a separate helper exists

`git commit` with no pathspec commits the **entire index**, which is easy to get wrong when
unrelated work is already staged — that mistake once produced a 54-file commit when 16 were
intended. `scripts/push-review.py` always shows the full file list and the exact branch before
asking, so the push contains what you think it contains.



