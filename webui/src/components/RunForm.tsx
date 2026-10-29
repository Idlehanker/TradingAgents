import { useState } from 'react'
import type { AppConfig, RunParams } from '../types'

const DEFAULT_ANALYSTS = ['market', 'social', 'news', 'fundamentals']

interface Props {
  config: AppConfig | null
  disabled: boolean
  onSubmit: (params: Partial<RunParams>) => Promise<void> | void
  error: string | null
  /** Another analysis is already running: this one joins the queue. */
  busy?: boolean
}

function today(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export function RunForm({ config, disabled, onSubmit, error, busy }: Props) {
  const [ticker, setTicker] = useState('NVDA')
  const [analysisDate, setAnalysisDate] = useState(today())
  const [assetType, setAssetType] = useState('stock')
  const [analysts, setAnalysts] = useState<string[]>(DEFAULT_ANALYSTS)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [deepModel, setDeepModel] = useState('')
  const [quickModel, setQuickModel] = useState('')
  const [debateRounds, setDebateRounds] = useState('')
  const [riskRounds, setRiskRounds] = useState('')
  const [language, setLanguage] = useState('')
  const [checkpoint, setCheckpoint] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const toggleAnalyst = (key: string) => {
    setAnalysts((previous) =>
      previous.includes(key) ? previous.filter((item) => item !== key) : [...previous, key],
    )
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!ticker.trim() || analysts.length === 0) return
    setSubmitting(true)
    try {
      await onSubmit({
        ticker: ticker.trim().toUpperCase(),
        analysis_date: analysisDate,
        asset_type: assetType,
        analysts,
        deep_think_llm: deepModel.trim() || null,
        quick_think_llm: quickModel.trim() || null,
        max_debate_rounds: debateRounds ? Number(debateRounds) : null,
        max_risk_rounds: riskRounds ? Number(riskRounds) : null,
        output_language: language.trim() || null,
        checkpoint_enabled: checkpoint,
      })
    } finally {
      setSubmitting(false)
    }
  }

  const locked = disabled || submitting

  return (
    <form className="card run-form" onSubmit={submit}>
      <h2 className="card__title">New analysis</h2>

      <label className="field">
        <span>Ticker</span>
        <input
          value={ticker}
          onChange={(event) => setTicker(event.target.value.toUpperCase())}
          placeholder="NVDA, AAPL, 0700.HK"
          spellCheck={false}
        />
      </label>

      <div className="field-row">
        <label className="field">
          <span>Analysis date</span>
          <input
            type="date"
            value={analysisDate}
            max={today()}
            onChange={(event) => setAnalysisDate(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Asset type</span>
          <select value={assetType} onChange={(event) => setAssetType(event.target.value)}>
            {(config?.asset_types ?? ['stock', 'crypto']).map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="field">
        <span>Analyst team</span>
        <div className="chips">
          {(config?.analysts ?? []).map((analyst) => (
            <button
              type="button"
              key={analyst.key}
              className={`chip chip--toggle ${analysts.includes(analyst.key) ? 'is-on' : ''}`}
              onClick={() => toggleAnalyst(analyst.key)}
            >
              {analyst.label.replace(' Analyst', '')}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        className="link-button"
        onClick={() => setShowAdvanced((previous) => !previous)}
      >
        {showAdvanced ? 'Hide model settings' : 'Model settings'}
      </button>

      {showAdvanced && (
        <div className="advanced">
          <label className="field">
            <span>Deep thinking model</span>
            <input
              value={deepModel}
              placeholder={config?.deep_think_llm ?? 'from .env'}
              onChange={(event) => setDeepModel(event.target.value)}
              spellCheck={false}
            />
          </label>
          <label className="field">
            <span>Quick thinking model</span>
            <input
              value={quickModel}
              placeholder={config?.quick_think_llm ?? 'from .env'}
              onChange={(event) => setQuickModel(event.target.value)}
              spellCheck={false}
            />
          </label>
          <div className="field-row">
            <label className="field">
              <span>Debate rounds</span>
              <input
                type="number"
                min={1}
                max={10}
                value={debateRounds}
                placeholder={String(config?.max_debate_rounds ?? 1)}
                onChange={(event) => setDebateRounds(event.target.value)}
              />
            </label>
            <label className="field">
              <span>Risk rounds</span>
              <input
                type="number"
                min={1}
                max={10}
                value={riskRounds}
                placeholder={String(config?.max_risk_discuss_rounds ?? 1)}
                onChange={(event) => setRiskRounds(event.target.value)}
              />
            </label>
          </div>
          <label className="field">
            <span>Output language</span>
            <select value={language} onChange={(event) => setLanguage(event.target.value)}>
              <option value="">Default ({config?.output_language ?? 'English'})</option>
              {(config?.languages ?? []).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={checkpoint}
              onChange={(event) => setCheckpoint(event.target.checked)}
            />
            <span>Enable checkpoint / resume</span>
          </label>
        </div>
      )}

      <button className="button button--primary" type="submit" disabled={locked || !ticker.trim()}>
        {submitting ? 'Starting…' : disabled ? 'Run in progress' : 'Start analysis'}
      </button>

      {busy && <p className="hint">A run is already active; this one queues behind it.</p>}
      {error && <p className="hint hint--error">{error}</p>}

      {config && (
        <p className="hint">
          Provider <code>{config.llm_provider}</code>
          {config.backend_url ? <> → <code>{config.backend_url}</code></> : null} · deep{' '}
          <code>{config.deep_think_llm}</code> · quick <code>{config.quick_think_llm}</code>
        </p>
      )}
    </form>
  )
}
