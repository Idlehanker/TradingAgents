import { useCallback, useEffect, useMemo, useState } from 'react'
import { ActivityStream } from './components/ActivityStream'
import { AgentBoard } from './components/AgentBoard'
import { DecisionPanel } from './components/DecisionPanel'
import { HistoryPanel } from './components/HistoryPanel'
import { ReportPanel } from './components/ReportPanel'
import { RunForm } from './components/RunForm'
import { RunsList } from './components/RunsList'
import { StatsBar } from './components/StatsBar'
import { StatusPill } from './components/ui'
import { api } from './api'
import { useRunStream } from './useRunStream'
import type { AppConfig, RunParams, RunSummary } from './types'

type View = 'live' | 'history'

export default function App() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [view, setView] = useState<View>('live')
  const [launchError, setLaunchError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const { run, connected } = useRunStream(activeId)

  const refreshRuns = useCallback(async () => {
    try {
      const response = await api.runs()
      setRuns(response.runs)
    } catch {
      /* the backend may still be starting; the next poll retries */
    }
  }, [])

  useEffect(() => {
    api.config().then(setConfig).catch(() => setConfig(null))
    void refreshRuns()
  }, [refreshRuns])

  const active = runs.some((run) => run.status === 'queued' || run.status === 'running')

  useEffect(() => {
    if (!active) return
    const poll = setInterval(() => void refreshRuns(), 3000)
    return () => clearInterval(poll)
  }, [active, refreshRuns])

  useEffect(() => {
    if (!active) return
    const seconds = setInterval(() => setTick((value) => value + 1), 1000)
    return () => clearInterval(seconds)
  }, [active])

  const elapsed = useMemo(() => {
    if (!run?.started_at) return 0
    const end = run.finished_at ?? Date.now() / 1000
    return tick >= 0 ? Math.max(0, end - run.started_at) : 0
  }, [run, tick])

  const startRun = async (params: Partial<RunParams>) => {
    setLaunchError(null)
    try {
      const response = await api.create(params)
      setView('live')
      setActiveId(response.id)
      await refreshRuns()
    } catch (error) {
      setLaunchError(String(error))
    }
  }

  const cancelRun = async () => {
    if (!activeId) return
    await api.cancel(activeId)
    await refreshRuns()
  }

  const summary = runs.find((item) => item.id === activeId)

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar__brand">
          <span className="topbar__logo">TA</span>
          <div>
            <h1>TradingAgents Console</h1>
            <p>Multi-agent analysis, streamed live from the graph</p>
          </div>
        </div>

        <div className="topbar__run">
          {summary ? (
            <>
              <strong>{summary.ticker}</strong>
              <span className="topbar__date">{summary.analysis_date}</span>
              <StatusPill status={run?.status ?? summary.status} />
            </>
          ) : (
            <span className="hint">No run selected</span>
          )}
        </div>

        <div className="topbar__actions">
          <nav className="tabs tabs--top">
            <button className={`tab ${view === 'live' ? 'is-active' : ''}`} onClick={() => setView('live')}>
              Live run
            </button>
            <button
              className={`tab ${view === 'history' ? 'is-active' : ''}`}
              onClick={() => setView('history')}
            >
              History
            </button>
          </nav>
          <button
            className="button button--danger"
            disabled={!summary || summary.status !== 'running'}
            onClick={() => void cancelRun()}
          >
            Cancel
          </button>
        </div>
      </header>

      {run && view === 'live' && <StatsBar run={run} elapsed={elapsed} connected={connected} />}

      <main className="workspace">
        <aside className="column column--side">
          <RunForm config={config} disabled={false} busy={active} onSubmit={startRun} error={launchError} />
          <section className="card">
            <header className="card__header">
              <h2 className="card__title">Runs</h2>
              <button className="link-button" onClick={() => void refreshRuns()}>
                Refresh
              </button>
            </header>
            <RunsList runs={runs} activeId={activeId} onSelect={(id) => { setActiveId(id); setView('live') }} />
          </section>
        </aside>

        {view === 'history' ? (
          <section className="column column--wide">
            <HistoryPanel />
          </section>
        ) : (
          <>
            <section className="column">
              {run ? <AgentBoard run={run} /> : <Empty selected={Boolean(summary)} />}
              {run && <ActivityStream run={run} />}
            </section>
            <section className="column">
              {run ? (
                <>
                  <DecisionPanel run={run} />
                  <ReportPanel run={run} />
                </>
              ) : null}
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function Empty({ selected }: { selected: boolean }) {
  return (
    <section className="card empty">
      <h2 className="card__title">{selected ? 'Loading run…' : 'Nothing selected'}</h2>
      <p className="hint">
        Start an analysis, or pick one from the runs list, to watch the agents work.
      </p>
    </section>
  )
}
