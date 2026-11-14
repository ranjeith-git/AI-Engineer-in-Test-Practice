import { useEffect, useId, useRef, useState } from 'react'
import { STATUSES, statusById } from '../constants.js'
import { emptyForm, formFromJob, validateJob } from '../jobs.js'

const FIELD_ORDER = [
  'company',
  'role',
  'status',
  'dateApplied',
  'url',
  'resumeUsed',
  'salary',
  'notes',
]

export default function JobForm({
  mode,
  job,
  initialStatus,
  resumeNames,
  saving,
  error,
  onSubmit,
  onClose,
  onDelete,
}) {
  const isEdit = mode === 'edit'
  const [values, setValues] = useState(() =>
    isEdit && job ? formFromJob(job) : emptyForm(initialStatus),
  )
  const [errors, setErrors] = useState({})
  const [attempted, setAttempted] = useState(false)

  const formRef = useRef(null)
  const firstRef = useRef(null)
  const resumeListId = useId()

  useEffect(() => {
    firstRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  function handleChange(name, value) {
    const next = { ...values, [name]: value }
    setValues(next)
    if (attempted) setErrors(validateJob(next))
  }

  function handleSubmit(event) {
    event.preventDefault()
    const found = validateJob(values)
    setAttempted(true)
    setErrors(found)

    const firstBad = FIELD_ORDER.find((name) => found[name])
    if (firstBad) {
      formRef.current?.querySelector(`[name="${firstBad}"]`)?.focus()
      return
    }
    onSubmit(values)
  }

  function fieldProps(name) {
    const message = errors[name]
    return {
      id: `job-${name}`,
      name,
      'aria-invalid': message ? true : undefined,
      'aria-describedby': message ? `job-${name}-error` : undefined,
    }
  }

  function errorFor(name) {
    if (!errors[name]) return null
    return (
      <span className="field__error" id={`job-${name}-error`}>
        {errors[name]}
      </span>
    )
  }

  return (
    <aside className="panel" aria-labelledby="editor-title">
      <header className="panel__head">
        <div className="panel__titles">
          <p className="panel__eyebrow">{isEdit ? 'Editing' : 'New job'}</p>
          <h2 className="panel__title" id="editor-title">
            {isEdit ? job.company : `Add to ${statusById(initialStatus).label}`}
          </h2>
        </div>
        <button type="button" className="btn btn--ghost" onClick={onClose}>
          Close
        </button>
      </header>

      <form className="form" ref={formRef} onSubmit={handleSubmit} noValidate>
        <fieldset className="form__group">
          <legend className="form__legend">The role</legend>

          <div className="field">
            <label className="field__label" htmlFor="job-company">
              Company
              <span className="field__tag">required</span>
            </label>
            <input
              {...fieldProps('company')}
              ref={firstRef}
              className="input"
              type="text"
              autoComplete="organization"
              placeholder="Acme Analytics"
              value={values.company}
              onChange={(event) => handleChange('company', event.target.value)}
            />
            {errorFor('company')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-role">
              Role
              <span className="field__tag">required</span>
            </label>
            <input
              {...fieldProps('role')}
              className="input"
              type="text"
              placeholder="Senior QA Engineer"
              value={values.role}
              onChange={(event) => handleChange('role', event.target.value)}
            />
            {errorFor('role')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-status">
              Column
            </label>
            <select
              {...fieldProps('status')}
              className="input"
              value={values.status}
              onChange={(event) => handleChange('status', event.target.value)}
            >
              {STATUSES.map((status) => (
                <option key={status.id} value={status.id}>
                  {status.label}: {status.meaning}
                </option>
              ))}
            </select>
            {errorFor('status')}
          </div>
        </fieldset>

        <fieldset className="form__group">
          <legend className="form__legend">The application</legend>

          <div className="field">
            <label className="field__label" htmlFor="job-dateApplied">
              Date applied
            </label>
            <input
              {...fieldProps('dateApplied')}
              className="input"
              type="date"
              value={values.dateApplied}
              onChange={(event) => handleChange('dateApplied', event.target.value)}
            />
            {errorFor('dateApplied')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-url">
              Job posting link
            </label>
            <input
              {...fieldProps('url')}
              className="input"
              type="url"
              inputMode="url"
              placeholder="https://linkedin.com/jobs/view/1234567890"
              value={values.url}
              onChange={(event) => handleChange('url', event.target.value)}
            />
            {errorFor('url')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-resumeUsed">
              Resume used
            </label>
            <input
              {...fieldProps('resumeUsed')}
              className="input"
              type="text"
              list={resumeListId}
              placeholder="QA_Lead_Resume"
              value={values.resumeUsed}
              onChange={(event) => handleChange('resumeUsed', event.target.value)}
            />
            <datalist id={resumeListId}>
              {resumeNames.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
            <span className="field__hint">
              Pick one you have used before, or type a new name to add it to the list.
            </span>
            {errorFor('resumeUsed')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-salary">
              Salary range
            </label>
            <input
              {...fieldProps('salary')}
              className="input"
              type="text"
              placeholder="₹25-30 LPA"
              value={values.salary}
              onChange={(event) => handleChange('salary', event.target.value)}
            />
            {errorFor('salary')}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="job-notes">
              Notes
            </label>
            <textarea
              {...fieldProps('notes')}
              className="input input--area"
              rows={4}
              placeholder="Recruiter name, referral, take-home task, interview panel."
              value={values.notes}
              onChange={(event) => handleChange('notes', event.target.value)}
            />
            {errorFor('notes')}
          </div>
        </fieldset>

        {error ? (
          <p className="form__error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="form__actions">
          <button type="submit" className="btn btn--primary" disabled={saving}>
            {saving ? 'Saving' : isEdit ? 'Save changes' : 'Add to board'}
          </button>
          <button type="button" className="btn btn--quiet" onClick={onClose}>
            Cancel
          </button>
          <span className="form__status" role="status">
            {saving ? 'Writing to this browser' : ''}
          </span>
        </div>

        {isEdit && onDelete ? (
          <div className="form__danger">
            <p className="form__danger-text">
              Removing takes it off the board. Undo is offered for a few seconds afterwards.
            </p>
            <button type="button" className="btn btn--danger-outline" disabled={saving} onClick={onDelete}>
              Remove job
            </button>
          </div>
        ) : null}
      </form>
    </aside>
  )
}
