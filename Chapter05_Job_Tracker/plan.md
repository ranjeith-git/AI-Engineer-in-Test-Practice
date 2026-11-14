# Chapter 5 - Job Tracker: Implementation Plan

**Goal:** a local-first Kanban board for tracking job applications. One Vite + React single-page
app, all data in the browser via IndexedDB, no backend, no accounts, no network calls. Open the
URL and the board is there; close the tab and nothing is lost.

**Decisions locked with the user**

| Decision | Choice |
|---|---|
| Stack | Vite + React, plain JavaScript, no TypeScript |
| Persistence | IndexedDB through the `idb` library (small async wrapper over the raw API) |
| Backend | None. No API, no auth, no sync |
| Board shape | 6 fixed columns (see below), drag-and-drop between them |
| Card fields | company, role, LinkedIn URL, resume used, date applied, salary, notes, status |
| Look | Clean and minimal, Linear / Trello restrained. Accent per status, not decoration |

---

## 1. Why IndexedDB and not localStorage

`localStorage` is synchronous, string-only, and capped around 5 MB. A job search is a growing
list held for months, with free-text notes and a URL per record. IndexedDB is asynchronous,
stores real objects, and has no realistic size ceiling. The `idb` wrapper turns its
event-callback API into promises so the data layer stays about ten lines per operation.

| Option | Verdict |
|---|---|
| `localStorage` | String serialisation on every write, 5 MB ceiling, no indexes |
| IndexedDB raw | Correct storage, painful callback API |
| **IndexedDB + `idb`** | **Correct storage, promise API, one small dependency** |
| SQLite/WASM | Real query power, paid for with a much larger bundle |

Nothing here needs SQL. Six columns over a few hundred records is an in-memory filter.

## 2. Data model

One object store, `jobs`, keyed by `id`, with indexes on `status` and `dateApplied`.

```js
{
  id:          "c2f1...",      // crypto.randomUUID()
  company:     "Acme",         // required
  role:        "QA Lead",      // required
  status:      "applied",      // one of the six column ids
  url:         "https://...",  // optional, LinkedIn job posting
  resumeUsed:  "QA_Lead_Resume",// optional, free text with suggestions
  dateApplied: "2026-09-16",   // YYYY-MM-DD, auto-set on create, editable
  salary:      "₹25-30 LPA",   // optional, free text
  notes:       "Recruiter: ...",// optional
  order:       1024,           // position inside its column
  createdAt:   "2026-09-16T...",
  updatedAt:   "2026-09-16T..."
}
```

`order` is a float so a card can be dropped between two neighbours without renumbering the
column: the new value is the midpoint of the two either side. Dragging to the bottom of a column
adds one to the last value.

## 3. Columns

Ordered as the pipeline, not the alphabet. Colour encodes progress as well as identity, so the
board is readable in greyscale (every card also carries the status as text).

| # | Id | Label | Meaning | Accent |
|---|---|---|---|---|
| 1 | `wishlist` | Wishlist | Saved, not applied to yet | slate |
| 2 | `applied` | Applied | Application submitted | blue |
| 3 | `followup` | Follow-up | Chased the recruiter or referral | amber |
| 4 | `interview` | Interview | In interview rounds | violet |
| 5 | `offer` | Offer | An offer is on the table | green |
| 6 | `rejected` | Rejected | Closed out | red, desaturated |

Rejected is deliberately the quietest of the six. A board you stop opening is worse than a
board that is ugly, and a wall of alarm-red is a wall you avoid.

## 4. Files

```
Chapter05_Job_Tracker/
├── plan.md                  # this file (deliverable)
├── README.md                # cold start, in every shell
├── package.json             # scripts: dev, build, preview, test
├── vite.config.js           # React plugin + Vitest config in one file
├── index.html               # Vite entry
├── .gitignore               # node_modules, dist, coverage
├── src/
│   ├── main.jsx             # mounts <App/>
│   ├── App.jsx              # state, persistence effects, modal, error banner
│   ├── db.js                # IndexedDB via idb: list / add / update / remove
│   ├── jobs.js              # pure logic: validation, defaults, ordering, grouping
│   ├── constants.js         # the six statuses, accents, seed resume names
│   ├── styles.css           # design tokens + every state
│   └── components/
│       ├── Board.jsx        # columns, drop targets, empty states
│       ├── JobCard.jsx      # one card + its drag/overflow behaviour
│       └── JobForm.jsx      # add/edit dialog with inline validation
└── tests/
    ├── setup.js             # jest-dom matchers, clean fake IndexedDB
    ├── jobs.test.js         # validation, defaults, ordering, grouping
    ├── db.test.js           # real CRUD against fake-indexeddb
    └── app.test.jsx         # add a job, validate, drag a card, reload
```

## 5. Layering

`jobs.js` holds every decision worth testing and touches no browser API. `db.js` only moves
objects in and out of IndexedDB. Components render and dispatch. That split is what makes the
suite fast and lets validation be tested without a DOM.

## 6. Behaviour and states

**Write path.** Add or edit through one dialog. Company and role are required. The save button
is never disabled: pressing it with an empty required field reveals the error and moves focus
there. A disabled button hides the thing that needs fixing.

**URL validation.** Only `http://` and `https://` are accepted; anything else fails with a
message showing the expected shape. A bare `linkedin.com/...` is accepted and normalised to
`https://linkedin.com/...`, because retyping a prefix to satisfy a form is a tax.

**Resume used.** A text input backed by a `datalist` built from every resume name already on the
board, seeded with a couple of examples. Typing a new name is allowed and it appears in the list
from then on, so the field gets more useful the longer the board is used.

**Drag and drop.** Native HTML5 drag events, no drag library. A card is `draggable`; columns and
cards are drop targets. Dropping on a card inserts above it, dropping on empty column space
appends. The moved card keeps its data and gains only a new `status` and `order`.

**States built, not deferred.** Loading (first read), empty board, empty column, error banner if
IndexedDB is unavailable or a write fails, overflow (long company names and long notes truncate
with the full value in the title, and cards never grow past a fixed line budget), focus-visible
on every control, disabled while a save is in flight, plus drag-in-progress styling on both the
card and the hovered column.

**Keyboard path.** The dialog traps focus, closes on Escape, and returns focus to the control
that opened it. Status is also a field in the dialog, so a card can be moved between columns
without a mouse.

**Motion.** Only what explains a state change: dialog entrance, drop-target highlight, save
confirmation. Everything is wrapped in `prefers-reduced-motion`.

## 7. Tests

Vitest with jsdom and `fake-indexeddb`, so the CRUD tests exercise a real IndexedDB
implementation. The suite covers:

- validation: required fields, URL normalisation and rejection, whitespace-only input
- defaults: `dateApplied` defaults to today, `status` defaults to `wishlist`, ids are unique
- ordering: midpoint insertion between neighbours, append at the end
- grouping: cards land in the right column, sorted, one column per status
- CRUD: create, read back, update a field, move between columns, delete
- UI: submitting empty shows errors, a valid submit writes a card, dragging moves a column,
  and a re-read returns the persisted value

## 8. Verification before handover

`npm test` green, `npm run build` clean, then the dev server started in the background and the
board exercised in a real browser: add a job, drag it through two columns, reload the page and
confirm the card is still where it was left. The localhost URL is handed over with the app
already running.

No mock data is seeded into the database. The board starts empty and says so.

## 9. Scope boundary

Not in this chapter: authentication, server sync, reminders, analytics, resume upload, multiple
boards. The `url` field links out to the posting; nothing scrapes it. This chapter tracks
applications, it does not apply to them.
