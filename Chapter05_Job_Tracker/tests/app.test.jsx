import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '../src/App.jsx'
import { listJobs, putJob, removeJob } from '../src/db.js'
import { makeJob } from '../src/jobs.js'

function makeDataTransfer() {
  const store = new Map()
  return {
    dropEffect: 'none',
    effectAllowed: 'none',
    types: [],
    setData: (type, value) => store.set(type, value),
    getData: (type) => store.get(type) ?? '',
    setDragImage: () => {},
  }
}

const column = (name) => screen.getByRole('region', { name })
const card = (role, company) => screen.getByLabelText(`${role} at ${company}`)

async function openBoard() {
  render(<App />)
  await screen.findByRole('button', { name: 'Add job' })
  await waitFor(() => expect(screen.queryByText('Reading your board')).not.toBeInTheDocument())
}

beforeEach(async () => {
  for (const job of await listJobs()) await removeJob(job.id)
})

describe('board', () => {
  it('shows the six columns in pipeline order', async () => {
    await openBoard()
    expect(screen.getAllByRole('region')).toHaveLength(6)
    expect(screen.getByRole('region', { name: 'Wishlist' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Rejected' })).toBeInTheDocument()
  })

  it('tells an empty column what belongs in it', async () => {
    await openBoard()
    expect(within(column('Wishlist')).getByText(/Nothing saved yet/)).toBeInTheDocument()
    expect(within(column('Interview')).getByText(/interview rounds start/i)).toBeInTheDocument()
  })

  it('puts a stored card in its column', async () => {
    await putJob(makeJob({ company: 'Nova Labs', role: 'QA Lead', status: 'interview' }))
    await openBoard()
    expect(within(column('Interview')).getByLabelText('QA Lead at Nova Labs')).toBeInTheDocument()
  })
})

describe('adding a job', () => {
  it('refuses an empty form and says what is missing', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(screen.getByRole('button', { name: 'Add job' }))
    await user.click(screen.getByRole('button', { name: 'Add to board' }))

    expect(screen.getByText('Add the company name.')).toBeInTheDocument()
    expect(screen.getByText('Add the role you are applying for.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Company/)).toHaveFocus()
    expect(await listJobs()).toHaveLength(0)
  })

  it('clears the message once the field is filled in', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(screen.getByRole('button', { name: 'Add job' }))
    await user.click(screen.getByRole('button', { name: 'Add to board' }))
    await user.type(screen.getByLabelText(/Company/), 'Acme Analytics')

    expect(screen.queryByText('Add the company name.')).not.toBeInTheDocument()
    expect(screen.getByText('Add the role you are applying for.')).toBeInTheDocument()
  })

  it('saves a complete job into the store and onto the board', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(screen.getByRole('button', { name: 'Add job' }))
    await user.type(screen.getByLabelText(/Company/), 'Acme Analytics')
    await user.type(screen.getByLabelText(/Role/), 'Senior QA Engineer')
    await user.type(screen.getByLabelText(/Resume used/), 'QA_Lead_Resume')
    await user.type(screen.getByLabelText(/Salary range/), '25-30 LPA')
    await user.click(screen.getByRole('button', { name: 'Add to board' }))

    expect(await screen.findByText('Job added to the board.')).toBeInTheDocument()
    const added = card('Senior QA Engineer', 'Acme Analytics')
    expect(within(column('Wishlist')).getByLabelText('Senior QA Engineer at Acme Analytics')).toBeInTheDocument()
    expect(within(added).getByText('QA_Lead_Resume')).toBeInTheDocument()

    const stored = await listJobs()
    expect(stored).toHaveLength(1)
    expect(stored[0]).toMatchObject({
      company: 'Acme Analytics',
      role: 'Senior QA Engineer',
      status: 'wishlist',
      resumeUsed: 'QA_Lead_Resume',
    })
  })

  it('repairs a link typed without a scheme', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(screen.getByRole('button', { name: 'Add job' }))
    await user.type(screen.getByLabelText(/Company/), 'Acme Analytics')
    await user.type(screen.getByLabelText(/Role/), 'Senior QA Engineer')
    await user.type(screen.getByLabelText(/Job posting link/), 'linkedin.com/jobs/view/99')
    await user.click(screen.getByRole('button', { name: 'Add to board' }))

    await waitFor(async () => expect(await listJobs()).toHaveLength(1))
    expect((await listJobs())[0].url).toBe('https://linkedin.com/jobs/view/99')
  })

  it('rejects a link that is not a web address', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(screen.getByRole('button', { name: 'Add job' }))
    await user.type(screen.getByLabelText(/Company/), 'Acme Analytics')
    await user.type(screen.getByLabelText(/Role/), 'Senior QA Engineer')
    await user.type(screen.getByLabelText(/Job posting link/), 'javascript:alert(1)')
    await user.click(screen.getByRole('button', { name: 'Add to board' }))

    expect(screen.getByText(/Use a full link/)).toBeInTheDocument()
    expect(await listJobs()).toHaveLength(0)
  })

  it('opens the editor already pointed at the column that was clicked', async () => {
    const user = userEvent.setup()
    await openBoard()

    await user.click(
      within(column('Offer')).getByRole('button', { name: 'Add a job to Offer' }),
    )
    expect(screen.getByRole('complementary', { name: 'Add to Offer' })).toBeInTheDocument()
    expect(screen.getByLabelText('Column')).toHaveValue('offer')
  })
})

describe('editing a job', () => {
  it('saves changed fields and moves the card to another column', async () => {
    const user = userEvent.setup()
    await putJob(makeJob({ company: 'Vertex', role: 'Automation Engineer' }))
    await openBoard()

    await user.click(within(card('Automation Engineer', 'Vertex')).getByRole('button', { name: 'Edit' }))
    const panel = screen.getByRole('complementary', { name: 'Vertex' })

    await user.clear(within(panel).getByLabelText(/Role/))
    await user.type(within(panel).getByLabelText(/Role/), 'Automation Lead')
    await user.selectOptions(within(panel).getByLabelText('Column'), 'offer')
    await user.click(within(panel).getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Changes saved.')).toBeInTheDocument()
    await waitFor(async () => {
      const [stored] = await listJobs()
      expect(stored.role).toBe('Automation Lead')
      expect(stored.status).toBe('offer')
    })
    expect(within(column('Offer')).getByLabelText('Automation Lead at Vertex')).toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the button that opened it', async () => {
    const user = userEvent.setup()
    await putJob(makeJob({ company: 'Vertex', role: 'Automation Engineer' }))
    await openBoard()

    const editButton = within(card('Automation Engineer', 'Vertex')).getByRole('button', { name: 'Edit' })
    await user.click(editButton)
    expect(screen.getByRole('complementary', { name: 'Vertex' })).toBeInTheDocument()

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(editButton).toHaveFocus()
  })
})

describe('moving cards', () => {
  it('drops a card into another column and persists it', async () => {
    await putJob(makeJob({ company: 'Nova Labs', role: 'QA Lead' }))
    await openBoard()

    const dataTransfer = makeDataTransfer()
    fireEvent.dragStart(within(card('QA Lead', 'Nova Labs')).getByTitle('Drag to move'), { dataTransfer })
    fireEvent.dragOver(column('Interview'), { dataTransfer })
    fireEvent.drop(column('Interview'), { dataTransfer })

    await waitFor(async () => {
      const [stored] = await listJobs()
      expect(stored.status).toBe('interview')
    })
    expect(within(column('Interview')).getByLabelText('QA Lead at Nova Labs')).toBeInTheDocument()
    expect(within(column('Wishlist')).queryByLabelText('QA Lead at Nova Labs')).not.toBeInTheDocument()
  })

  it('drops a card onto another card and lands above it', async () => {
    await putJob(makeJob({ company: 'First', role: 'QA Lead', order: 10 }))
    await putJob(makeJob({ company: 'Second', role: 'SDET', order: 20 }))
    await openBoard()

    const dataTransfer = makeDataTransfer()
    fireEvent.dragStart(within(card('SDET', 'Second')).getByTitle('Drag to move'), { dataTransfer })
    fireEvent.dragOver(card('QA Lead', 'First'), { dataTransfer })
    fireEvent.drop(card('QA Lead', 'First'), { dataTransfer })

    await waitFor(async () => {
      const stored = await listJobs()
      const moved = stored.find((job) => job.company === 'Second')
      const anchor = stored.find((job) => job.company === 'First')
      expect(moved.order).toBeLessThan(anchor.order)
      expect(moved.status).toBe(anchor.status)
    })
  })
})

describe('removing a job', () => {
  it('deletes it and offers an undo that puts it back', async () => {
    const user = userEvent.setup()
    await putJob(makeJob({ company: 'Orbit', role: 'SDET' }))
    await openBoard()

    await user.click(within(card('SDET', 'Orbit')).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('Removed Orbit.')).toBeInTheDocument()
    expect(await listJobs()).toHaveLength(0)
    expect(screen.queryByLabelText('SDET at Orbit')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Undo' }))

    await waitFor(async () => expect(await listJobs()).toHaveLength(1))
    expect(await screen.findByLabelText('SDET at Orbit')).toBeInTheDocument()
  })
})
