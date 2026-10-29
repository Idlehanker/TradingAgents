/** Shapes returned by /api and pushed over /ws. */

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type AgentStatus = 'pending' | 'in_progress' | 'completed' | 'error'

export interface RunParams {
  ticker: string
  analysis_date: string
  asset_type: string
  analysts: string[]
  quick_think_llm: string | null
  deep_think_llm: string | null
  max_debate_rounds: number | null
  max_risk_rounds: number | null
  output_language: string | null
  checkpoint_enabled: boolean
}

export interface ActivityMessage {
  ts: string
  type: string
  content: string
  /** Stream sequence, used to interleave messages with tool calls. */
  seq?: number
}

export interface ToolCallRecord {
  ts: string
  name: string
  args: Record<string, unknown>
  seq?: number
}

export interface ReportView {
  section: string
  title: string
  agent: string
  content: string | null
}

export interface Decision {
  rating: string
  is_review: boolean
  text: string
  fields: Record<string, string>
}

export interface RunStats {
  llm_calls: number
  tool_calls: number
  tokens_in: number
  tokens_out: number
}

export interface RunSnapshot {
  id: string
  params: RunParams
  status: RunStatus
  created_at: number
  started_at: number | null
  finished_at: number | null
  elapsed: number
  error: string | null
  messages: ActivityMessage[]
  tool_calls: ToolCallRecord[]
  agents: Record<string, AgentStatus>
  teams: Record<string, string[]>
  reports: Record<string, ReportView>
  stats: RunStats
  decision: Decision | null
  report_path: string | null
}

export interface RunSummary {
  id: string
  ticker: string
  analysis_date: string
  status: RunStatus
  created_at: number
  elapsed: number
  agents_completed: number
  agents_total: number
  rating: string | null
  error: string | null
}

export interface AnalystOption {
  key: string
  label: string
}

export interface AppConfig {
  llm_provider: string | null
  backend_url: string | null
  deep_think_llm: string | null
  quick_think_llm: string | null
  quick_think_provider: string | null
  deep_think_provider: string | null
  max_debate_rounds: number
  max_risk_discuss_rounds: number
  output_language: string | null
  checkpoint_enabled: boolean
  results_dir: string
  data_cache_dir: string
  analysts: AnalystOption[]
  languages: string[]
  asset_types: string[]
  busy: boolean
}

export interface HistoryRow {
  ticker: string
  trade_date: string
  rating: string | null
  excerpt: string
  decision: string
  run_settings: Record<string, unknown>
  updated_at: number
}

export interface StreamEvent {
  seq: number
  type: 'snapshot' | 'status' | 'message' | 'tool_call' | 'agents' | 'report' | 'stats' | 'decision' | 'error'
  data: Record<string, unknown>
  ts: number
}
