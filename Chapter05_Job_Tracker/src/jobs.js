import { DEFAULT_STATUS, RESUME_SUGGESTIONS, STATUSES, STATUS_IDS } from './constants.js'

export function newId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `job_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
}

export function todayISO(now = new Date()) {
  const date = new Date(now)
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function toDate(isoDate) {
  const [year, month, day] = String(isoDate).split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatDate(isoDate) {
  if (!isISODate(isoDate)) return ''
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(toDate(isoDate))
}

export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function isISODate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const [year, month, day] = value.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  )
}

export function isHttpUrl(value) {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

export function normalizeUrl(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return ''
  if (/^https?:\/\//i.test(value)) return value
  if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/i.test(value)) return `https://${value}`
  return value
}

export function validateJob(input) {
  const errors = {}
  const company = String(input.company ?? '').trim()
  const role = String(input.role ?? '').trim()
  const url = normalizeUrl(input.url)
  const dateApplied = String(input.dateApplied ?? '').trim()
  const status = input.status ?? DEFAULT_STATUS

  if (!company) errors.company = 'Add the company name.'
  if (!role) errors.role = 'Add the role you are applying for.'
  if (url && !isHttpUrl(url)) errors.url = 'Use a full link, for example https://linkedin.com/jobs/view/123'
  if (dateApplied && !isISODate(dateApplied)) errors.dateApplied = 'Use a real date in YYYY-MM-DD form.'
  if (!STATUS_IDS.includes(status)) errors.status = 'Pick one of the six columns.'

  return errors
}

export function makeJob(input, options = {}) {
  const now = options.now ?? new Date()
  const timestamp = new Date(now).toISOString()

  return {
    id: options.id ?? newId(),
    company: String(input.company ?? '').trim(),
    role: String(input.role ?? '').trim(),
    status: STATUS_IDS.includes(input.status) ? input.status : DEFAULT_STATUS,
    url: normalizeUrl(input.url),
    resumeUsed: String(input.resumeUsed ?? '').trim(),
    dateApplied: String(input.dateApplied ?? '').trim() || todayISO(now),
    salary: String(input.salary ?? '').trim(),
    notes: String(input.notes ?? '').trim(),
    order: typeof input.order === 'number' ? input.order : 1024,
    createdAt: timestamp,
    updatedAt: timestamp,
  }
}

export function applyEdit(job, input, options = {}) {
  const now = options.now ?? new Date()
  return {
    ...job,
    company: String(input.company ?? '').trim(),
    role: String(input.role ?? '').trim(),
    status: STATUS_IDS.includes(input.status) ? input.status : job.status,
    url: normalizeUrl(input.url),
    resumeUsed: String(input.resumeUsed ?? '').trim(),
    dateApplied: String(input.dateApplied ?? '').trim() || job.dateApplied,
    salary: String(input.salary ?? '').trim(),
    notes: String(input.notes ?? '').trim(),
    order: typeof input.order === 'number' ? input.order : job.order,
    updatedAt: new Date(now).toISOString(),
  }
}

export function emptyForm(defaultStatus = DEFAULT_STATUS, now = new Date()) {
  return {
    company: '',
    role: '',
    status: defaultStatus,
    url: '',
    resumeUsed: '',
    dateApplied: todayISO(now),
    salary: '',
    notes: '',
  }
}

export function formFromJob(job) {
  return {
    company: job.company ?? '',
    role: job.role ?? '',
    status: job.status ?? DEFAULT_STATUS,
    url: job.url ?? '',
    resumeUsed: job.resumeUsed ?? '',
    dateApplied: job.dateApplied ?? '',
    salary: job.salary ?? '',
    notes: job.notes ?? '',
  }
}

export function compareJobs(a, b) {
  if (a.order !== b.order) return a.order - b.order
  return String(b.createdAt).localeCompare(String(a.createdAt))
}

export function groupByStatus(jobs) {
  const groups = {}
  for (const status of STATUSES) groups[status.id] = []

  for (const job of jobs) {
    const column = STATUS_IDS.includes(job.status) ? job.status : DEFAULT_STATUS
    groups[column].push(job)
  }

  for (const column of Object.keys(groups)) groups[column].sort(compareJobs)
  return groups
}

export function topOrder(columnJobs) {
  if (!columnJobs.length) return 1024
  return Math.min(...columnJobs.map((job) => job.order)) - 1
}

export function dropOrder(columnJobs, movingId, targetId) {
  const list = columnJobs.filter((job) => job.id !== movingId)

  if (!targetId) {
    const last = list[list.length - 1]
    return last ? last.order + 1 : 1024
  }

  const index = list.findIndex((job) => job.id === targetId)
  if (index === -1) {
    const last = list[list.length - 1]
    return last ? last.order + 1 : 1024
  }

  const before = index > 0 ? list[index - 1].order : null
  const after = list[index].order
  if (before === null) return after - 1
  return (before + after) / 2
}

export function collectResumeNames(jobs, seeds = RESUME_SUGGESTIONS) {
  const seen = new Map()
  for (const name of [...seeds, ...jobs.map((job) => job.resumeUsed)]) {
    const value = String(name ?? '').trim()
    if (!value) continue
    const key = value.toLowerCase()
    if (!seen.has(key)) seen.set(key, value)
  }
  return [...seen.values()].sort((a, b) => a.localeCompare(b))
}
