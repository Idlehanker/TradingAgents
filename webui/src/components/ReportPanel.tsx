import { useEffect, useMemo, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { RunSnapshot } from '../types'

interface Props {
  run: RunSnapshot
}

export function ReportPanel({ run }: Props) {
  const reports = useMemo(() => Object.values(run.reports ?? {}), [run.reports])
  const [active, setActive] = useState<string | null>(null)

  useEffect(() => {
    setActive((previous) => {
      if (previous && reports.some((report) => report.section === previous)) return previous
      const ready = reports.find((report) => report.content)
      return ready?.section ?? reports[0]?.section ?? null
    })
  }, [reports])

  const current = reports.find((report) => report.section === active)

  return (
    <section className="card report-panel">
      <header className="card__header">
        <h2 className="card__title">Reports</h2>
        <span className="card__badge">
          {reports.filter((report) => report.content).length}/{reports.length}
        </span>
      </header>

      <nav className="tabs">
        {reports.map((report) => (
          <button
            key={report.section}
            className={`tab ${report.section === active ? 'is-active' : ''} ${report.content ? 'is-ready' : ''}`}
            onClick={() => setActive(report.section)}
          >
            {report.title}
          </button>
        ))}
      </nav>

      <div className="report-panel__body">
        {!current ? (
          <p className="hint">No reports yet.</p>
        ) : !current.content ? (
          <p className="hint">
            Waiting for <strong>{current.agent}</strong> to file this section…
          </p>
        ) : (
          <div className="markdown">
            <Markdown remarkPlugins={[remarkGfm]}>{current.content}</Markdown>
          </div>
        )}
      </div>
    </section>
  )
}
