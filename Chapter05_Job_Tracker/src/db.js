import { openDB } from 'idb'

export const DB_NAME = 'job-tracker'
export const DB_VERSION = 1
export const STORE = 'jobs'

let handle = null

function db() {
  if (!handle) {
    handle = openDB(DB_NAME, DB_VERSION, {
      upgrade(database) {
        if (database.objectStoreNames.contains(STORE)) return
        const store = database.createObjectStore(STORE, { keyPath: 'id' })
        store.createIndex('status', 'status')
        store.createIndex('dateApplied', 'dateApplied')
      },
    }).catch((error) => {
      handle = null
      throw error
    })
  }
  return handle
}

export async function listJobs() {
  return (await db()).getAll(STORE)
}

export async function getJob(id) {
  return (await db()).get(STORE, id)
}

export async function putJob(job) {
  await (await db()).put(STORE, job)
  return job
}

export async function removeJob(id) {
  await (await db()).delete(STORE, id)
}
