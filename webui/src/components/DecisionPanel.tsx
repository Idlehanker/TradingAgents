import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { RatingBadge } from './ui'
import type { RunSnapshot } from '../types'

interface Props {
  run: RunSnapshot
}

const HEADLINE_FIELDS = ['rating', 'price target', 'time horizon', 'confidence']

export function DecisionPanel({ run }: Props) {
  if (run.status === 'failed') {
    return (
      <section className="card decision decision--error">
        <h2 className="card__title">Run failed</h2>
        <pre className="stack-trace">{run.error}</pre>
      </section>
    )
  }

  const decision = run.decision
  if (!decision) {
    return (
      <section className="card decision">
        <h2 className="card__title">Final decision</h2>
        <p className="hint">
          {run.status === 'cancelled'
            ? 'Run cancelled before a decision was reached.'
            : 'The Portfolio Manager has not ruled yet.'}
        </p>
      </section>
    )
  }

  const headlines = Object.entries(decision.fields).filter(([key]) => HEADLINE_FIELDS.includes(key))
  const narrative = Object.entries(decision.fields).filter(([key]) => !HEADLINE_FIELDS.includes(key))

  return (
    <section className="card decision">
      <header className="card__header">
        <h2 className="card__title">Portfolio Manager decision</h2>
        <RatingBadge rating={decision.rating} isReview={decision.is_review} />
      </header>

      {headlines.length > 0 && (
        <dl className="decision__fields">
          {headlines.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}

      {narrative.length > 0 && (
        <dl className="decision__narrative">
          {narrative.map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="markdown">
        <Markdown remarkPlugins={[remarkGfm]}>{decision.text}</Markdown>
      </div>

      {run.report_path && <p className="hint">Saved to <code>{run.report_path}</code></p>}
    </section>
  )
}
