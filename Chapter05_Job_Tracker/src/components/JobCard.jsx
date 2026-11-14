import { useRef } from 'react'
import { formatDate, hostOf } from '../jobs.js'

export default function JobCard({
  job,
  dragging,
  dropAbove,
  dragActive,
  saving,
  onDragStart,
  onDragEnd,
  onDragOverCard,
  onDropOnCard,
  onEdit,
  onDelete,
}) {
  const cardRef = useRef(null)

  const classes = ['card']
  if (dragging) classes.push('card--dragging')
  if (dropAbove) classes.push('card--drop-above')

  return (
    <article
      className={classes.join(' ')}
      ref={cardRef}
      aria-label={`${job.role} at ${job.company}`}
      onDragOver={(event) => {
        if (!dragActive) return
        event.preventDefault()
        event.stopPropagation()
        event.dataTransfer.dropEffect = 'move'
        onDragOverCard(job.id)
      }}
      onDrop={(event) => {
        if (!dragActive) return
        event.preventDefault()
        event.stopPropagation()
        onDropOnCard(job.id)
      }}
    >
      <div className="card__top">
        <span
          className="card__grip"
          role="presentation"
          title="Drag to move"
          draggable={!saving}
          onDragStart={(event) => {
            event.dataTransfer.effectAllowed = 'move'
            event.dataTransfer.setData('text/plain', job.id)
            event.dataTransfer.setDragImage?.(cardRef.current, 16, 16)
            onDragStart(job.id)
          }}
          onDragEnd={onDragEnd}
        >
          <svg viewBox="0 0 10 16" width="10" height="16" aria-hidden="true" focusable="false">
            <circle cx="2" cy="3" r="1.4" />
            <circle cx="8" cy="3" r="1.4" />
            <circle cx="2" cy="8" r="1.4" />
            <circle cx="8" cy="8" r="1.4" />
            <circle cx="2" cy="13" r="1.4" />
            <circle cx="8" cy="13" r="1.4" />
          </svg>
        </span>

        <div className="card__titles">
          <h3 className="card__company" title={job.company}>
            {job.company}
          </h3>
          <p className="card__role" title={job.role}>
            {job.role}
          </p>
        </div>
      </div>

      <div className="card__body">
        <ul className="chips">
          <li className="chip">{formatDate(job.dateApplied)}</li>
          {job.resumeUsed ? (
            <li className="chip" title={job.resumeUsed}>
              {job.resumeUsed}
            </li>
          ) : null}
          {job.salary ? (
            <li className="chip chip--money" title={job.salary}>
              {job.salary}
            </li>
          ) : null}
        </ul>

        {job.notes ? (
          <p className="card__notes" title={job.notes}>
            {job.notes}
          </p>
        ) : null}
      </div>

      <footer className="card__foot">
        {job.url ? (
          <a className="card__link" href={job.url} target="_blank" rel="noreferrer" title={job.url}>
            {hostOf(job.url) || 'Posting'}
          </a>
        ) : (
          <span className="card__link card__link--muted">No posting link</span>
        )}

        <div className="card__actions">
          <button type="button" className="btn btn--ghost" onClick={(event) => onEdit(job, event)}>
            Edit
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--danger"
            disabled={saving}
            onClick={() => onDelete(job)}
          >
            Delete
          </button>
        </div>
      </footer>
    </article>
  )
}
