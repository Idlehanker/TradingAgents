import { useEffect, useRef, useState } from 'react'
import type {
  ActivityMessage,
  AgentStatus,
  Decision,
  ReportView,
  RunSnapshot,
  RunStats,
  RunStatus,
  StreamEvent,
  ToolCallRecord,
} from './types'

const MAX_ROWS = 400
const RETRY_MS = 1500

function applyEvent(previous: RunSnapshot, event: StreamEvent): RunSnapshot {
  switch (event.type) {
    case 'snapshot':
      return event.data as unknown as RunSnapshot
    case 'status':
      return { ...previous, status: event.data.status as RunStatus }
    case 'message': {
      const message = event.data.message as ActivityMessage
      const messages = [...previous.messages, { ...message, seq: event.seq }]
      return { ...previous, messages: messages.slice(-MAX_ROWS) }
    }
    case 'tool_call': {
      const toolCall = event.data.tool_call as ToolCallRecord
      const tool_calls = [...previous.tool_calls, { ...toolCall, seq: event.seq }]
      return { ...previous, tool_calls: tool_calls.slice(-MAX_ROWS) }
    }
    case 'agents':
      return { ...previous, agents: event.data.agents as Record<string, AgentStatus> }
    case 'report': {
      const report = event.data as unknown as ReportView
      return { ...previous, reports: { ...previous.reports, [report.section]: report } }
    }
    case 'stats':
      return { ...previous, stats: event.data.stats as RunStats }
    case 'decision':
      return { ...previous, decision: event.data.decision as Decision }
    case 'error':
      return { ...previous, error: String(event.data.error ?? '') }
    default:
      return previous
  }
}

function socketUrl(runId: string): string {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
  const base = import.meta.env.VITE_WS_BASE ?? ''
  return base
    ? `${base}/ws/runs/${runId}`
    : `${scheme}://${location.host}/ws/runs/${runId}`
}

/**
 * Keeps one run's snapshot live: REST once, then WebSocket deltas. Reconnects
 * while the run is unfinished so a dropped connection does not freeze the view.
 */
export function useRunStream(runId: string | null) {
  const [run, setRun] = useState<RunSnapshot | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const attempts = useRef(0)

  useEffect(() => {
    if (!runId) {
      setRun(null)
      return
    }
    setRun(null)
    setError(null)
    attempts.current = 0

    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let closed = false

    const connect = () => {
      if (closed) return
      socket = new WebSocket(socketUrl(runId))
      socket.onopen = () => {
        attempts.current = 0
        setConnected(true)
      }
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as StreamEvent
          setRun((previous) => (previous === null && payload.type !== 'snapshot'
            ? previous
            : applyEvent(previous ?? ({} as RunSnapshot), payload)))
        } catch (parseError) {
          setError(`Bad stream payload: ${String(parseError)}`)
        }
      }
      socket.onerror = () => setConnected(false)
      socket.onclose = (event) => {
        setConnected(false)
        // 4404: the server has no such run (it forgot it on restart), so a
        // retry would only repeat the failure. Otherwise retry a few rounds.
        if (closed || event.code === 4404 || attempts.current > 5) return
        attempts.current += 1
        retry = setTimeout(connect, RETRY_MS)
      }
    }

    connect()
    return () => {
      closed = true
      if (retry) clearTimeout(retry)
      if (socket) socket.close()
    }
  }, [runId])

  return { run, connected, error }
}
