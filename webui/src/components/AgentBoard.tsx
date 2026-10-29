import { agentLabel } from './ui'
import type { AgentStatus, RunSnapshot } from '../types'

interface Props {
  run: RunSnapshot
}

const REPORT_OWNER: Record<string, string> = {
  market_report: 'Market Analyst',
  sentiment_report: 'Sentiment Analyst',
  news_report: 'News Analyst',
  fundamentals_report: 'Fundamentals Analyst',
  bull_history: 'Bull Researcher',
  bear_history: 'Bear Researcher',
  investment_plan: 'Research Manager',
  trader_investment_plan: 'Trader',
  risk_aggressive: 'Aggressive Analyst',
  risk_conservative: 'Conservative Analyst',
  risk_neutral: 'Neutral Analyst',
  final_trade_decision: 'Portfolio Manager',
}

export function AgentBoard({ run }: Props) {
  const teams = Object.entries(run.teams ?? {})
  const statuses = Object.values(run.agents ?? {})
  const done = statuses.filter((status) => status === 'completed').length
  const percent = statuses.length === 0 ? 0 : Math.round((done / statuses.length) * 100)
  const writing = Object.entries(run.reports ?? {}).find(
    ([, report]) => report.content && REPORT_OWNER[report.section],
  )

  return (
    <section className="card agent-board">
      <header className="card__header">
        <h2 className="card__title">Agent pipeline</h2>
        <span className="card__badge">
          {done}/{statuses.length}
        </span>
      </header>

      <div className="progress">
        <div className="progress__bar" style={{ width: `${percent}%` }} />
      </div>

      <div className="teams">
        {teams.map(([team, agents]) => (
          <div className="team" key={team}>
            <h3>{team}</h3>
            {agents.map((agent) => {
              const status = (run.agents?.[agent] ?? 'pending') as AgentStatus
              const report = Object.values(run.reports ?? {}).find((item) => item.agent === agent)
              return (
                <div className={`agent agent--${status}`} key={agent}>
                  <span className="agent__dot" />
                  <span className="agent__name">{agent}</span>
                  {report?.content && <span className="agent__report">report ready</span>}
                  <span className={`agent__status agent__status--${status}`}>
                    {agentLabel(status)}
                  </span>
                </div>
              )
            })}
          </div>
        ))}
      </div>

      {writing && (
        <p className="hint">
          Writing: <code>{writing[1].title}</code>
        </p>
      )}
    </section>
  )
}
