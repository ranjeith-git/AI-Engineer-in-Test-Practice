# Chapter 5 - Job Tracker

A local-first Kanban board for a job search. Six columns from Wishlist to Rejected, drag cards
between them, and every field you care about on one card: company, role, LinkedIn link, which
resume you sent, the date, the salary band, and notes.

**There is no backend, no account, and no network request.** Everything you type is stored in
IndexedDB inside your own browser. Nothing leaves the machine.

## Layout

```
Chapter05_Job_Tracker/
├── plan.md                  # design and decisions (deliverable)
├── package.json             # scripts: dev, build, preview, test
├── vite.config.js           # React plugin + Vitest config
├── index.html
├── src/
│   ├── main.jsx             # mounts the app
│   ├── App.jsx              # state, storage writes, editor panel, undo toast
│   ├── db.js                # IndexedDB access through idb
│   ├── jobs.js              # validation, defaults, column ordering, grouping
│   ├── constants.js         # the six columns and their accents
│   ├── styles.css
│   └── components/
│       ├── Board.jsx        # columns, drag targets, empty states
│       ├── JobCard.jsx      # one card
│       └── JobForm.jsx      # add/edit panel with inline validation
└── tests/                   # Vitest: pure logic, storage, and the UI end to end
```

## One-time setup

Node 20.19+ is required (this machine runs Node 24). Then, from the chapter folder:

**PowerShell**
```powershell
cd "C:\Users\Ranjeith\AI Testing\Chapter05_Job_Tracker"
npm install --include=dev
```

**cmd**
```cmd
cd /d "C:\Users\Ranjeith\AI Testing\Chapter05_Job_Tracker"
npm install --include=dev
```

**macOS / Linux**
```bash
cd "Chapter05_Job_Tracker"
npm install --include=dev
```

> `--include=dev` matters on this machine. `NODE_ENV=production` is set in the shell, and npm 11
> then skips `devDependencies` while still reporting success. Without the flag, Vite and Vitest
> are never installed and `npm run dev` fails with `'vite' is not recognized`.

## Running it

```powershell
npm run dev
```

Open **http://localhost:5173** in your browser. The port is pinned with `--strictPort` on
purpose: IndexedDB is scoped to the origin, so if Vite silently moved to `:5174` your board would
look empty. If the port is busy, Vite stops and says so instead of quietly relocating your data.

To stop the server, press `Ctrl+C` in that terminal.

Production build, if you want a static copy:

```powershell
npm run build      # writes dist/
npm run preview    # serves dist/ on http://localhost:4173
```

## Using the board

- **Add job** in the top right opens the editor. The `+` on any column header opens it with that
  column already selected.
- **Company** and **Role** are required. The save button stays clickable either way; pressing it
  with a field missing marks the field and puts the cursor in it.
- **Drag a card by the grip** on its left edge and drop it on another column, or on a card to
  land above it. Dropping in the empty space at the bottom of a column appends it.
- **No mouse needed.** Open a card with **Edit** and change the **Column** dropdown; that moves
  it just like a drag does.
- **Resume used** offers every name already on your board, plus two seeds. Type a new one and it
  joins the list, so the suggestions get better the more you use it.
- **Delete** removes the card and offers **Undo** for a few seconds. It does not ask first.
- **Job posting link** opens in a new tab. A bare `linkedin.com/jobs/view/123` is accepted and
  stored as `https://linkedin.com/jobs/view/123`.

## Columns

| Column | What it means | Accent |
|---|---|---|
| Wishlist | Saved, not applied to yet | slate |
| Applied | Application submitted | blue |
| Follow-up | Chased the recruiter or referral | amber |
| Interview | In interview rounds | violet |
| Offer | An offer is on the table | green |
| Rejected | Closed out | red, muted |

## Where your data lives

In IndexedDB, database `job-tracker`, store `jobs`, for the origin `http://localhost:5173`.

- To inspect it: DevTools (`F12`) → **Application** → **IndexedDB** → `job-tracker` → `jobs`.
- To wipe it: right click `job-tracker` in that panel and delete the database, then reload.
- It is per browser and per origin. A different browser, a private window, or a different port
  will all show an empty board. That is the whole point of local-first, but it does mean there is
  no built-in backup. Export is not implemented in this chapter.

## Tests

```powershell
npm run test        # one pass, 48 tests
npm run test:watch  # re-run on change
```

The suite runs against a real IndexedDB implementation (`fake-indexeddb`) in jsdom, so the storage
tests are not mocks. It covers required-field validation, URL repair and rejection, date handling,
column ordering when a card is dropped between two neighbours, grouping, create/read/update/delete,
and the UI end to end: refusing an empty form, saving a job, dragging a card to another column,
editing a card into another column, and the delete-then-undo round trip.

`NODE_ENV=production` would otherwise make React load its production test utilities; `vite.config.js`
sets `NODE_ENV=test` for the test run so that does not bite.

## Scope

In this chapter: one board, six columns, local storage. Out of scope on purpose: login, server
sync, reminders, analytics, resume upload, and multiple boards. The link field links out to the
posting; nothing scrapes it. This tracks applications, it does not apply to them.
