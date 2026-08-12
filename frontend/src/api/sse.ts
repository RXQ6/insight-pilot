import type { TaskEvent } from '../types'

const EVENT_NAMES = [
  'status',
  'tool_call',
  'token',
  'chart',
  'approval_required',
  'result',
  'done',
  'error',
]

export interface SseHandlers {
  onEvent?: (event: TaskEvent) => void
  onError?: () => void
}

export function connectTaskEvents(
  taskId: string,
  token: string,
  handlers: SseHandlers,
): EventSource {
  const baseURL = import.meta.env.VITE_API_BASE ?? '/api'
  const url = `${baseURL}/tasks/${taskId}/events?token=${encodeURIComponent(token)}`
  const source = new EventSource(url)

  EVENT_NAMES.forEach((name) => {
    source.addEventListener(name, (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as Record<string, unknown>
        handlers.onEvent?.({ type: name as TaskEvent['type'], ...data })
      } catch {
        // ignore malformed events
      }
    })
  })

  source.onerror = () => handlers.onError?.()
  return source
}
