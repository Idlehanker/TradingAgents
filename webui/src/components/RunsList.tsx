import { formatClock, StatusPill } from './ui'
import type { RunSummary } from '../types'

interface Props {
  runs: RunSummary[]
  activeId: string | null
  onSelect: (runId: string) => void
}

export function RunsList({ runs, activeId, onSelect }: Props) {
  if (runs.length === 0) {
    return <p className="hint">No runs yet — start one above.</p>
  }

  return (
    <ul className="runs">
      {runs.map((run) => (
        <li key={run.id}>
          <button
            className={`run-row ${run.id === activeId ? 'is-active' : ''}`}
            onClick={() => onSelect(run.id)}
          >
            <span className="run-row__head">
              <strong>{run.ticker}</strong>
              <StatusPill status={run.status} />
            </span>
            <span className="run-row__meta">
              {run.analysis_date} · {run.agents_completed}/{run.agents_total} agents ·{' '}
              {formatClock(run.elapsed)}
            </span>
            {run.rating && <span className="run-row__rating">{run.rating}</span>}
            {run.error && <span className="run-row__error">{run.error.split('\n')[0]}</span>}
          </button>
        </li>
      ))}
    </ul>
  )
}
