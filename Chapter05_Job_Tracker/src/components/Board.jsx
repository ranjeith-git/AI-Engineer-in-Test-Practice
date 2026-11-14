import { useState } from 'react'
import JobCard from './JobCard.jsx'

const EMPTY_COPY = {
  wishlist: 'Nothing saved yet. Add a role you are considering, then move it along as you apply.',
  applied: 'Drop a card here once the application is in.',
  followup: 'Drop a card here after you chase the recruiter or referral.',
  interview: 'Drop a card here when the interview rounds start.',
  offer: 'Drop a card here when an offer lands.',
  rejected: 'Drop a card here when it closes out.',
}

export default function Board({
  statuses,
  columns,
  loading,
  saving,
  onDrop,
  onEdit,
  onDelete,
  onAdd,
}) {
  const [dragId, setDragId] = useState(null)
  const [over, setOver] = useState({ status: null, card: null })

  const endDrag = () => {
    setDragId(null)
    setOver({ status: null, card: null })
  }

  const dropOnColumn = (statusId) => {
    if (!dragId) return
    onDrop(dragId, statusId, null)
    endDrag()
  }

  const dropOnCard = (statusId, cardId) => {
    if (!dragId || dragId === cardId) {
      endDrag()
      return
    }
    onDrop(dragId, statusId, cardId)
    endDrag()
  }

  return (
    <div className="board" aria-busy={loading || undefined}>
      {statuses.map((status) => {
        const jobs = columns[status.id] ?? []
        const columnIsTarget = dragId !== null && over.status === status.id && over.card === null

        return (
          <section
            key={status.id}
            className={`column${columnIsTarget ? ' column--target' : ''}${dragId ? ' column--dragging' : ''}`}
            style={{ '--status-accent': status.accent }}
            aria-labelledby={`column-${status.id}`}
            onDragOver={(event) => {
              if (!dragId) return
              event.preventDefault()
              event.dataTransfer.dropEffect = 'move'
              setOver({ status: status.id, card: null })
            }}
            onDrop={(event) => {
              if (!dragId) return
              event.preventDefault()
              dropOnColumn(status.id)
            }}
          >
            <header className="column__head">
              <span className="column__dot" aria-hidden="true" />
              <h2 className="column__title" id={`column-${status.id}`}>
                {status.label}
              </h2>
              <span className="column__count">{jobs.length}</span>
              <button
                type="button"
                className="column__add"
                aria-label={`Add a job to ${status.label}`}
                title={`Add to ${status.label}`}
                disabled={saving}
                onClick={(event) => onAdd(status.id, event)}
              >
                <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false">
                  <path d="M6 1v10M1 6h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            </header>

            <p className="column__meaning" title={status.meaning}>
              {status.meaning}
            </p>

            <div className="column__scroll">
              {loading ? (
                <ul className="column__list" aria-hidden="true">
                  <li>
                    <div className="card card--skeleton" />
                  </li>
                  <li>
                    <div className="card card--skeleton" />
                  </li>
                </ul>
              ) : jobs.length ? (
                <ul className="column__list">
                  {jobs.map((job) => (
                    <li key={job.id}>
                      <JobCard
                        job={job}
                        dragging={dragId === job.id}
                        dropAbove={over.card === job.id && dragId !== job.id}
                        dragActive={dragId !== null && dragId !== job.id}
                        saving={saving}
                        onDragStart={(id) => {
                          setDragId(id)
                          setOver({ status: status.id, card: null })
                        }}
                        onDragEnd={endDrag}
                        onDragOverCard={(cardId) => setOver({ status: status.id, card: cardId })}
                        onDropOnCard={(cardId) => dropOnCard(status.id, cardId)}
                        onEdit={onEdit}
                        onDelete={onDelete}
                      />
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="column__empty">{EMPTY_COPY[status.id]}</p>
              )}
            </div>
          </section>
        )
      })}
    </div>
  )
}
