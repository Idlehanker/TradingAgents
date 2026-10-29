import type { AgentStatus, RunStatus } from '../types'

const STATUS_LABEL: Record<RunStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

export function statusLabel(status: RunStatus): string {
  return STATUS_LABEL[status] ?? status
}

export function agentLabel(status: AgentStatus): string {
  return status.replace('_', ' ')
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(total / 60)
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

export function formatTokens(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value)
}

export function formatTime(epoch: number | null): string {
  return epoch ? new Date(epoch * 1000).toLocaleString() : '—'
}

export function StatusPill({ status }: { status: RunStatus }) {
  return <span className={`pill pill--${status}`}>{statusLabel(status)}</span>
}

const RATING_KEYS = ['Buy', 'Overweight', 'Hold', 'Underweight', 'Sell', 'REVIEW']

export function RatingBadge({ rating, isReview }: { rating: string; isReview?: boolean }) {
  const tone = isReview || !RATING_KEYS.includes(rating) ? 'review' : rating.toLowerCase()
  return <span className={`rating rating--${tone.toLowerCase()}`}>{rating}</span>
}
