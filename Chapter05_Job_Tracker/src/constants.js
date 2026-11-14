export const STATUSES = [
  {
    id: 'wishlist',
    label: 'Wishlist',
    meaning: 'Saved, not applied to yet',
    accent: 'oklch(0.55 0.02 265)',
  },
  {
    id: 'applied',
    label: 'Applied',
    meaning: 'Application submitted',
    accent: 'oklch(0.55 0.13 250)',
  },
  {
    id: 'followup',
    label: 'Follow-up',
    meaning: 'Chased the recruiter or referral',
    accent: 'oklch(0.62 0.12 70)',
  },
  {
    id: 'interview',
    label: 'Interview',
    meaning: 'In interview rounds',
    accent: 'oklch(0.55 0.14 300)',
  },
  {
    id: 'offer',
    label: 'Offer',
    meaning: 'An offer is on the table',
    accent: 'oklch(0.56 0.12 155)',
  },
  {
    id: 'rejected',
    label: 'Rejected',
    meaning: 'Closed out',
    accent: 'oklch(0.55 0.07 25)',
  },
]

export const STATUS_IDS = STATUSES.map((status) => status.id)

export const DEFAULT_STATUS = 'wishlist'

export const RESUME_SUGGESTIONS = ['SDE_Resume_v3', 'QA_Lead_Resume']

export function statusById(id) {
  return STATUSES.find((status) => status.id === id) ?? STATUSES[0]
}
