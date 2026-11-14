import { describe, expect, it } from 'vitest'
import {
  applyEdit,
  collectResumeNames,
  dropOrder,
  emptyForm,
  formatDate,
  groupByStatus,
  hostOf,
  isHttpUrl,
  makeJob,
  normalizeUrl,
  topOrder,
  todayISO,
  validateJob,
} from '../src/jobs.js'

const valid = { company: 'Acme Analytics', role: 'Senior QA Engineer' }

describe('validateJob', () => {
  it('asks for the two required fields when the form is empty', () => {
    const errors = validateJob(emptyForm())
    expect(errors.company).toBe('Add the company name.')
    expect(errors.role).toBe('Add the role you are applying for.')
    expect(errors.dateApplied).toBeUndefined()
    expect(errors.url).toBeUndefined()
  })

  it('treats whitespace as missing', () => {
    const errors = validateJob({ ...valid, company: '   ', role: '\t\n' })
    expect(errors.company).toBeTruthy()
    expect(errors.role).toBeTruthy()
  })

  it('accepts a complete job', () => {
    expect(validateJob({ ...valid, url: 'https://linkedin.com/jobs/view/1' })).toEqual({})
  })

  it('rejects a link that is not http', () => {
    const errors = validateJob({ ...valid, url: 'javascript:alert(1)' })
    expect(errors.url).toMatch(/full link/i)
  })

  it('accepts a bare domain and infers https', () => {
    expect(validateJob({ ...valid, url: 'linkedin.com/jobs/view/1' })).toEqual({})
  })

  it('rejects an impossible date', () => {
    const errors = validateJob({ ...valid, dateApplied: '2026-02-31' })
    expect(errors.dateApplied).toMatch(/real date/i)
  })

  it('rejects a date in the wrong shape', () => {
    expect(validateJob({ ...valid, dateApplied: '16/09/2026' }).dateApplied).toBeTruthy()
  })

  it('rejects a column that does not exist', () => {
    expect(validateJob({ ...valid, status: 'ghosted' }).status).toBeTruthy()
  })
})

describe('url handling', () => {
  it('leaves an empty link empty', () => {
    expect(normalizeUrl('')).toBe('')
    expect(normalizeUrl(undefined)).toBe('')
  })

  it('adds https to a bare host', () => {
    expect(normalizeUrl('linkedin.com/jobs/view/42')).toBe('https://linkedin.com/jobs/view/42')
  })

  it('keeps an existing scheme', () => {
    expect(normalizeUrl('http://jobs.example.com/1')).toBe('http://jobs.example.com/1')
  })

  it('only trusts http and https', () => {
    expect(isHttpUrl('https://example.com')).toBe(true)
    expect(isHttpUrl('ftp://example.com')).toBe(false)
    expect(isHttpUrl('nonsense')).toBe(false)
  })

  it('shows the host without www', () => {
    expect(hostOf('https://www.linkedin.com/jobs/view/1')).toBe('linkedin.com')
    expect(hostOf('not a url')).toBe('')
  })
})

describe('dates', () => {
  it('formats today in local time, not UTC', () => {
    expect(todayISO(new Date(2026, 8, 16, 23, 30))).toBe('2026-09-16')
    expect(todayISO(new Date(2026, 0, 1, 0, 15))).toBe('2026-01-01')
  })

  it('renders a readable date and refuses rubbish', () => {
    expect(formatDate('2026-09-16')).toMatch(/2026/)
    expect(formatDate('16/09/2026')).toBe('')
  })
})

describe('makeJob', () => {
  it('fills in the defaults', () => {
    const job = makeJob(valid, { now: new Date(2026, 8, 16, 9) })
    expect(job.status).toBe('wishlist')
    expect(job.dateApplied).toBe('2026-09-16')
    expect(job.createdAt).toBe(job.updatedAt)
    expect(job.id).toBeTruthy()
  })

  it('gives every job a different id', () => {
    const ids = new Set(Array.from({ length: 50 }, () => makeJob(valid).id))
    expect(ids.size).toBe(50)
  })

  it('trims what was typed', () => {
    const job = makeJob({ ...valid, company: '  Acme  ', notes: '  ping Priya  ' })
    expect(job.company).toBe('Acme')
    expect(job.notes).toBe('ping Priya')
  })

  it('falls back to wishlist for an unknown column', () => {
    expect(makeJob({ ...valid, status: 'ghosted' }).status).toBe('wishlist')
  })
})

describe('applyEdit', () => {
  it('keeps identity and updates the timestamp', () => {
    const job = makeJob(valid, { now: new Date(2026, 8, 16, 9) })
    const edited = applyEdit(
      job,
      { ...valid, role: 'QA Lead', salary: ' 25 LPA ' },
      { now: new Date(2026, 8, 17, 9) },
    )
    expect(edited.id).toBe(job.id)
    expect(edited.createdAt).toBe(job.createdAt)
    expect(edited.role).toBe('QA Lead')
    expect(edited.salary).toBe('25 LPA')
    expect(edited.updatedAt).not.toBe(job.updatedAt)
  })

  it('ignores an unknown column rather than losing the card', () => {
    const job = makeJob({ ...valid, status: 'applied' })
    expect(applyEdit(job, { ...valid, status: 'ghosted' }).status).toBe('applied')
  })
})

describe('ordering', () => {
  const a = makeJob(valid, { id: 'a' })
  const b = makeJob(valid, { id: 'b' })

  it('appends to the end of an empty column', () => {
    expect(dropOrder([], 'x', null)).toBe(1024)
    expect(dropOrder([a], 'x', null)).toBe(a.order + 1)
  })

  it('slots a card above its target', () => {
    const first = { ...a, order: 10 }
    const second = { ...b, order: 20 }
    const order = dropOrder([first, second], 'moving', 'b')
    expect(order).toBeGreaterThan(10)
    expect(order).toBeLessThan(20)
  })

  it('slots a card above the first card without colliding', () => {
    expect(dropOrder([{ ...a, order: 10 }], 'moving', 'a')).toBeLessThan(10)
  })

  it('puts a new card on top of its column', () => {
    expect(topOrder([])).toBe(1024)
    expect(topOrder([{ order: 5 }, { order: 9 }])).toBe(4)
  })
})

describe('groupByStatus', () => {
  it('gives every column a bucket, sorted by order', () => {
    const groups = groupByStatus([
      makeJob({ ...valid, order: 20 }, { id: 'later' }),
      makeJob({ ...valid, order: 10 }, { id: 'first' }),
      makeJob({ ...valid, status: 'applied' }, { id: 'applied' }),
    ])

    expect(Object.keys(groups)).toHaveLength(6)
    expect(groups.wishlist.map((job) => job.id)).toEqual(['first', 'later'])
    expect(groups.applied.map((job) => job.id)).toEqual(['applied'])
    expect(groups.offer).toEqual([])
  })

  it('sweeps an unknown column into wishlist rather than dropping the card', () => {
    const groups = groupByStatus([makeJob({ ...valid, status: 'ghosted' })])
    expect(groups.wishlist).toHaveLength(1)
  })
})

describe('collectResumeNames', () => {
  it('seeds the list and keeps one spelling per name', () => {
    const names = collectResumeNames([
      makeJob({ ...valid, resumeUsed: 'qa_lead_resume' }),
      makeJob({ ...valid, resumeUsed: 'SDE_Resume_v4' }),
      makeJob({ ...valid, resumeUsed: '   ' }),
    ])
    expect(names).toContain('QA_Lead_Resume')
    expect(names).toContain('SDE_Resume_v4')
    expect(names.filter((name) => name.toLowerCase() === 'qa_lead_resume')).toHaveLength(1)
  })
})
