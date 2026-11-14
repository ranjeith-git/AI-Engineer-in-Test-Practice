import { beforeEach, describe, expect, it } from 'vitest'
import { getJob, listJobs, putJob, removeJob } from '../src/db.js'
import { makeJob, todayISO } from '../src/jobs.js'

const valid = { company: 'Acme Analytics', role: 'Senior QA Engineer' }

beforeEach(async () => {
  for (const job of await listJobs()) await removeJob(job.id)
})

describe('job storage', () => {
  it('starts empty', async () => {
    expect(await listJobs()).toEqual([])
  })

  it('writes a job and reads it back whole', async () => {
    const job = makeJob({ ...valid, url: 'https://linkedin.com/jobs/view/1', salary: '25-30 LPA' })
    await putJob(job)

    const stored = await getJob(job.id)
    expect(stored).toEqual(job)
    expect(stored.dateApplied).toBe(todayISO())
  })

  it('lists every job written', async () => {
    await putJob(makeJob({ ...valid, company: 'One' }))
    await putJob(makeJob({ ...valid, company: 'Two' }))
    expect(await listJobs()).toHaveLength(2)
  })

  it('overwrites on the same id instead of duplicating', async () => {
    const job = makeJob(valid)
    await putJob(job)
    await putJob({ ...job, status: 'interview' })

    const all = await listJobs()
    expect(all).toHaveLength(1)
    expect(all[0].status).toBe('interview')
  })

  it('deletes a job', async () => {
    const job = makeJob(valid)
    await putJob(job)
    await removeJob(job.id)

    expect(await listJobs()).toEqual([])
    expect(await getJob(job.id)).toBeUndefined()
  })

  it('returns undefined for an id that was never stored', async () => {
    expect(await getJob('missing')).toBeUndefined()
  })
})
