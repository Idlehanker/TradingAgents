import { useCallback, useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api'
import { RatingBadge } from './ui'
import type { HistoryRow } from '../types'

interface PastDecision {
  ticker: string
  trade_date: string
  rating: string | null
  decision: string
  reports: Record<string, string>
}

export function HistoryPanel() {
  const [rows, setRows] = useState<HistoryRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)
  const [detail, setDetail] = useState<PastDecision | null>(null)

  const load = useCallback(async () => {
    try {
      const response = await api.history()
      setRows(response.decisions)
      setError(null)
    } catch (requestError) {
      setError(String(requestError))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const select = async (row: HistoryRow) => {
    const key = `${row.ticker}-${row.trade_date}`
    if (open === key) {
      setOpen(null)
      setDetail(null)
      return
    }
    setOpen(key)
    setDetail(null)
    try {
      setDetail(await api.pastDecision(row.ticker, row.trade_date))
    } catch (requestError) {
      setError(String(requestError))
    }
  }

  return (
    <section className="card history">
      <header className="card__header">
        <h2 className="card__title">Recorded decisions</h2>
        <button className="link-button" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      {error && <p className="hint hint--error">{error}</p>}
      {rows.length === 0 && <p className="hint">Nothing recorded yet.</p>}

      <ul className="history__list">
        {rows.map((row) => {
          const key = `${row.ticker}-${row.trade_date}`
          return (
            <li key={key}>
              <button
                className={`history__row ${open === key ? 'is-active' : ''}`}
                onClick={() => void select(row)}
              >
                <span className="history__head">
                  <strong>{row.ticker}</strong>
                  <span className="history__date">{row.trade_date}</span>
                  {row.rating && <RatingBadge rating={row.rating} />}
                </span>
                <span className="history__excerpt">{row.excerpt}</span>
              </button>
              {open === key && detail && (
                <div className="markdown history__detail">
                  <Markdown remarkPlugins={[remarkGfm]}>{detail.decision}</Markdown>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
