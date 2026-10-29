import { useMemo, useState } from 'react'
import type { RunSnapshot } from '../types'

interface Props {
  run: RunSnapshot
}

interface Row {
  key: string
  seq: number
  kind: 'message' | 'tool'
  ts: string
  label: string
  detail: string
  args?: Record<string, unknown>
}

const FILTERS = ['all', 'agent', 'tool', 'data', 'system'] as const
type Filter = (typeof FILTERS)[number]

function buildRows(run: RunSnapshot): Row[] {
  const rows: Row[] = []
  run.messages.forEach((message, index) => {
    rows.push({
      key: `m-${index}-${message.ts}-${message.seq ?? index}`,
      seq: message.seq ?? index,
      kind: 'message',
      ts: message.ts,
      label: message.type,
      detail: message.content,
    })
  })
  run.tool_calls.forEach((call, index) => {
    const args = Object.entries(call.args ?? {})
      .map(([key, value]) => `${key}=${typeof value === 'string' ? value : JSON.stringify(value)}`)
      .join(', ')
    rows.push({
      key: `t-${index}-${call.ts}-${call.seq ?? index}`,
      seq: call.seq ?? index,
      kind: 'tool',
      ts: call.ts,
      label: 'Tool',
      detail: `${call.name}(${args})`,
      args: call.args,
    })
  })
  return rows.sort((a, b) => a.seq - b.seq)
}

export function ActivityStream({ run }: Props) {
  const [filter, setFilter] = useState<Filter>('all')
  const [newestFirst, setNewestFirst] = useState(true)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const rows = useMemo(() => {
    const built = buildRows(run).filter((row) => {
      if (filter === 'all') return true
      if (filter === 'tool') return row.kind === 'tool'
      return row.kind === 'message' && row.label.toLowerCase() === filter
    })
    return newestFirst ? built.slice().reverse() : built
  }, [run, filter, newestFirst])

  return (
    <section className="card activity">
      <header className="card__header">
        <h2 className="card__title">Live activity</h2>
        <div className="activity__controls">
          <div className="chips">
            {FILTERS.map((option) => (
              <button
                key={option}
                className={`chip ${filter === option ? 'is-on' : ''}`}
                onClick={() => setFilter(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <button className="link-button" onClick={() => setNewestFirst((previous) => !previous)}>
            {newestFirst ? 'Newest first' : 'Oldest first'}
          </button>
        </div>
      </header>

      <div className="activity__body">
        {rows.length === 0 && <p className="hint">Waiting for the first message…</p>}
        {rows.map((row) => {
          const isLong = row.detail.length > 220
          const open = expanded[row.key] || !isLong
          return (
            <article className={`entry entry--${row.kind} entry--${row.label.toLowerCase()}`} key={row.key}>
              <div className="entry__head">
                <span className="entry__time">{row.ts}</span>
                <span className="entry__label">{row.label}</span>
                {isLong && (
                  <button
                    className="link-button"
                    onClick={() => setExpanded((previous) => ({ ...previous, [row.key]: !open }))}
                  >
                    {open ? 'collapse' : 'expand'}
                  </button>
                )}
              </div>
              <pre className={`entry__detail ${open ? '' : 'is-clamped'}`}>{row.detail}</pre>
            </article>
          )
        })}
      </div>
    </section>
  )
}
