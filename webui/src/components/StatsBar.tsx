import { formatClock, formatTokens } from './ui'
import type { RunSnapshot } from '../types'

interface Props {
  run: RunSnapshot
  elapsed: number
  connected: boolean
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric__value">{value}</span>
      <span className="metric__label">{label}</span>
    </div>
  )
}

export function StatsBar({ run, elapsed, connected }: Props) {
  const agents = Object.values(run.agents ?? {})
  const completed = agents.filter((status) => status === 'completed').length
  const ready = Object.values(run.reports ?? {}).filter((report) => report.content).length
  const total = Object.keys(run.reports ?? {}).length

  return (
    <div className="stats">
      <Metric label="elapsed" value={formatClock(elapsed)} />
      <Metric label="LLM calls" value={String(run.stats?.llm_calls ?? 0)} />
      <Metric label="tool calls" value={String(run.stats?.tool_calls ?? 0)} />
      <Metric label="tokens ↑" value={formatTokens(run.stats?.tokens_in ?? 0)} />
      <Metric label="tokens ↓" value={formatTokens(run.stats?.tokens_out ?? 0)} />
      <Metric label="agents" value={`${completed}/${agents.length}`} />
      <Metric label="reports" value={`${ready}/${total}`} />
      <Metric label="stream" value={connected ? 'live' : 'offline'} />
    </div>
  )
}
