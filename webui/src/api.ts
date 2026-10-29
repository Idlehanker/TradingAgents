import type { AppConfig, HistoryRow, RunSnapshot, RunSummary, RunParams } from './types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status}: ${detail.slice(0, 300)}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ ok: boolean; busy: boolean }>('/api/health'),
  config: () => request<AppConfig>('/api/config'),
  runs: () => request<{ runs: RunSummary[] }>('/api/runs'),
  run: (id: string) => request<RunSnapshot>(`/api/runs/${id}`),
  create: (params: Partial<RunParams>) =>
    request<{ id: string; status: string; snapshot: RunSnapshot }>('/api/runs', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  cancel: (id: string) => request<{ cancelled: boolean }>(`/api/runs/${id}/cancel`, { method: 'POST' }),
  history: (limit = 30) => request<{ decisions: HistoryRow[] }>(`/api/history?limit=${limit}`),
  pastDecision: (ticker: string, tradeDate: string) =>
    request<{ ticker: string; trade_date: string; rating: string | null; decision: string; reports: Record<string, string> }>(
      `/api/history/${encodeURIComponent(ticker)}/${encodeURIComponent(tradeDate)}`,
    ),
}
