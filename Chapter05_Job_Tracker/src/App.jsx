import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Board from './components/Board.jsx'
import JobForm from './components/JobForm.jsx'
import { DEFAULT_STATUS, STATUSES } from './constants.js'
import * as store from './db.js'
import {
  applyEdit,
  collectResumeNames,
  dropOrder,
  groupByStatus,
  makeJob,
  topOrder,
} from './jobs.js'

const UNDO_WINDOW_MS = 6000
const NARROW_QUERY = '(max-width: 900px)'

function useIsNarrow(query = NARROW_QUERY) {
  const [matches, setMatches] = useState(() => globalThis.matchMedia?.(query).matches ?? false)

  useEffect(() => {
    const list = globalThis.matchMedia?.(query)
    if (!list) return undefined
    setMatches(list.matches)
    const onChange = (event) => setMatches(event.matches)
    list.addEventListener('change', onChange)
    return () => list.removeEventListener('change', onChange)
  }, [query])

  return matches
}

function describeError(error) {
  const name = error?.name ?? ''
  if (name === 'SecurityError' || name === 'InvalidStateError') {
    return 'This browser is blocking local storage for the page. Private windows often do. Open the app in a normal window, or allow site data, then reload.'
  }
  if (name === 'QuotaExceededError') {
    return 'The browser is out of storage space for this site. Free some space, then try again.'
  }
  return `The write did not go through. ${error?.message ?? 'Unknown storage error.'}`
}

export default function App() {
  const [jobs, setJobs] = useState([])
  const [phase, setPhase] = useState('loading')
  const [loadError, setLoadError] = useState('')
  const [writeError, setWriteError] = useState('')
  const [editor, setEditor] = useState(null)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState(null)

  const triggerRef = useRef(null)
  const addButtonRef = useRef(null)
  const narrow = useIsNarrow()

  const load = useCallback(async () => {
    setPhase('loading')
    setLoadError('')
    try {
      setJobs(await store.listJobs())
      setPhase('ready')
    } catch (error) {
      setLoadError(describeError(error))
      setPhase('failed')
    }
  }, [])

  useEffect(() => {
    let alive = true
    store
      .listJobs()
      .then((all) => {
        if (!alive) return
        setJobs(all)
        setPhase('ready')
      })
      .catch((error) => {
        if (!alive) return
        setLoadError(describeError(error))
        setPhase('failed')
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(null), UNDO_WINDOW_MS)
    return () => clearTimeout(timer)
  }, [notice])

  const columns = useMemo(() => groupByStatus(jobs), [jobs])
  const resumeNames = useMemo(() => collectResumeNames(jobs), [jobs])
  const total = jobs.length

  const runWrite = useCallback(async (work) => {
    setSaving(true)
    setWriteError('')
    try {
      await work()
      setJobs(await store.listJobs())
      return true
    } catch (error) {
      setWriteError(describeError(error))
      return false
    } finally {
      setSaving(false)
    }
  }, [])

  const openEditor = useCallback((next, event) => {
    triggerRef.current = event?.currentTarget ?? null
    setWriteError('')
    setEditor(next)
  }, [])

  const closeEditor = useCallback(() => {
    setEditor(null)
    const trigger = triggerRef.current
    triggerRef.current = null
    if (trigger?.isConnected) trigger.focus()
    else addButtonRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(
    async (values) => {
      const isEdit = editor?.mode === 'edit'
      const succeeded = await runWrite(async () => {
        if (isEdit) {
          const movedColumn = groupByStatus(jobs)[values.status] ?? []
          const patch =
            values.status === editor.job.status
              ? values
              : { ...values, order: topOrder(movedColumn) }
          await store.putJob(applyEdit(editor.job, patch))
          return
        }
        const column = groupByStatus(jobs)[values.status] ?? []
        await store.putJob(makeJob(values, { order: topOrder(column) }))
      })

      if (!succeeded) return
      const added = !isEdit
      setEditor(null)
      setNotice({
        id: `save-${Date.now()}`,
        message: added ? 'Job added to the board.' : 'Changes saved.',
      })
      if (added) addButtonRef.current?.focus()
      else triggerRef.current?.isConnected && triggerRef.current.focus()
      triggerRef.current = null
    },
    [editor, jobs, runWrite],
  )

  const handleDrop = useCallback(
    (jobId, targetStatus, targetId = null) => {
      const job = jobs.find((candidate) => candidate.id === jobId)
      if (!job) return
      const column = groupByStatus(jobs)[targetStatus] ?? []
      const order = dropOrder(column, jobId, targetId)
      if (job.status === targetStatus && job.order === order) return

      runWrite(async () => {
        await store.putJob({
          ...job,
          status: targetStatus,
          order,
          updatedAt: new Date().toISOString(),
        })
      })
    },
    [jobs, runWrite],
  )

  const handleDelete = useCallback(
    (job) => {
      const snapshot = { ...job }
      runWrite(async () => {
        await store.removeJob(job.id)
        if (editor?.job?.id === job.id) setEditor(null)
      }).then((succeeded) => {
        if (!succeeded) return
        setNotice({
          id: `removed-${Date.now()}`,
          message: `Removed ${snapshot.company}.`,
          undo: snapshot,
        })
      })
    },
    [editor, runWrite],
  )

  const handleUndo = useCallback(() => {
    const job = notice?.undo
    if (!job) return
    setNotice(null)
    runWrite(() => store.putJob(job))
  }, [notice, runWrite])

  if (phase === 'failed') {
    return (
      <main className="fallback">
        <h1>Your board could not be opened</h1>
        <p className="fallback__body">{loadError}</p>
        <button type="button" className="btn btn--primary" onClick={load}>
          Try again
        </button>
      </main>
    )
  }

  return (
    <div className="app">
      <div className="main" inert={editor && narrow ? true : undefined}>
        <header className="appbar">
          <div className="appbar__titles">
            <h1 className="appbar__title">Job tracker</h1>
            <p className="appbar__note">
              {phase === 'loading'
                ? 'Reading your board'
                : total === 0
                  ? 'Saved in this browser only'
                  : `${total} ${total === 1 ? 'application' : 'applications'} in this browser`}
            </p>
          </div>
          <button
            type="button"
            className="btn btn--primary"
            ref={addButtonRef}
            onClick={(event) => openEditor({ mode: 'create', status: DEFAULT_STATUS }, event)}
          >
            Add job
          </button>
        </header>

        {writeError ? (
          <div className="banner" role="alert">
            <p className="banner__text">{writeError}</p>
            <button type="button" className="btn btn--quiet" onClick={() => setWriteError('')}>
              Dismiss
            </button>
          </div>
        ) : null}

        <Board
          statuses={STATUSES}
          columns={columns}
          loading={phase === 'loading'}
          saving={saving}
          onDrop={handleDrop}
          onEdit={(job, event) => openEditor({ mode: 'edit', job }, event)}
          onDelete={handleDelete}
          onAdd={(status, event) => openEditor({ mode: 'create', status }, event)}
        />
      </div>

      {editor ? (
        <button
          type="button"
          className="scrim"
          aria-label="Close the editor"
          onClick={closeEditor}
        />
      ) : null}

      {editor ? (
        <JobForm
          key={editor.mode === 'edit' ? editor.job.id : `create-${editor.status}`}
          mode={editor.mode}
          job={editor.job}
          initialStatus={editor.status ?? DEFAULT_STATUS}
          resumeNames={resumeNames}
          saving={saving}
          error={writeError}
          onSubmit={handleSubmit}
          onClose={closeEditor}
          onDelete={editor.mode === 'edit' ? () => handleDelete(editor.job) : null}
        />
      ) : null}

      <div className="toaster" aria-live="polite" role="status">
        {notice ? (
          <div className="toast">
            <p className="toast__text">{notice.message}</p>
            {notice.undo ? (
              <button type="button" className="btn btn--quiet" onClick={handleUndo}>
                Undo
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
