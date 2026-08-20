import { create } from 'zustand'
import { connectTaskEvents } from '../api/sse'
import { sessionApi } from '../api/sessions'
import { taskApi } from '../api/tasks'
import type { ChartSpec, FileEvent, Message, TaskEvent, TaskOutput, ToolCallEvent } from '../types'

export interface TaskMetrics {
  latencyMs: number
  tokenIn: number
  tokenOut: number
  costCny: number
}

function parseContent(raw: unknown): unknown {
  if (typeof raw !== 'string') {
    return raw
  }
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

interface ApprovalState {
  taskId: string
  reason: string
}

interface ChatState {
  messages: Message[]
  status: string
  streaming: string
  chart: ChartSpec | null
  toolCalls: ToolCallEvent[]
  approval: ApprovalState | null
  metrics: TaskMetrics | null
  pendingFile: FileEvent | null
  pendingTaskId: string | null
  loadMessages: (sessionId: number) => Promise<void>
  send: (sessionId: number, text: string) => Promise<void>
  resolveApproval: (approved: boolean) => Promise<void>
  clear: () => void
}

export const useChatStore = create<ChatState>((set) => {
  const handleEvent = (event: TaskEvent) => {
    const content = parseContent(event.content)
    switch (event.type) {
      case 'status': {
        const status = typeof content === 'string' ? content : event.status
        if (status) {
          set({ status })
        }
        break
      }
      case 'tool_call': {
        const call = asRecord(content)
        set((state) => ({
          toolCalls: [
            ...state.toolCalls,
            {
              name: (call.name as string) ?? event.tool ?? event.args?.name,
              arguments: (call.arguments as Record<string, unknown>) ?? event.args,
              status: (call.status as string) ?? 'running',
            } as ToolCallEvent,
          ],
        }))
        break
      }
      case 'token':
        if (typeof content === 'string') {
          set((state) => ({ streaming: state.streaming + content }))
        }
        break
      case 'chart': {
        const spec = (event.chartSpec ?? content) as ChartSpec | null
        if (spec) {
          set({ chart: spec })
        }
        break
      }
      case 'approval_required': {
        const record = asRecord(content)
        set({
          approval: {
            taskId: (record.taskId as string) ?? event.taskId ?? '',
            reason: (record.reason as string) ?? (typeof content === 'string' ? content : '需要人工确认'),
          },
        })
        break
      }
      case 'result': {
        const output = (content as TaskOutput) ?? event.output
        set((state) => ({
          messages: [
            ...state.messages,
            {
              role: 'assistant',
              content: output?.answer ?? '已完成分析',
              chart: output?.chartSpec ?? null,
              file: state.pendingFile,
              taskId: state.pendingTaskId,
              createdAt: new Date().toISOString(),
            },
          ],
          streaming: '',
          pendingFile: null,
        }))
        break
      }
      case 'file': {
        const file = (event.file ?? content) as FileEvent | null
        if (file && file.filename) {
          set({ pendingFile: file })
        }
        break
      }
      case 'done': {
        const record = asRecord(content)
        set({
          status: 'done',
          metrics: {
            latencyMs: Number(record.latencyMs ?? 0),
            tokenIn: Number(record.tokenIn ?? 0),
            tokenOut: Number(record.tokenOut ?? 0),
            costCny: Number(record.costCny ?? 0),
          },
        })
        break
      }
      case 'error':
        set((state) => ({
          status: 'error',
          messages: [
            ...state.messages,
            {
              role: 'assistant',
              content: typeof content === 'string' ? content : '执行失败',
              createdAt: new Date().toISOString(),
            },
          ],
          streaming: '',
        }))
        break
      default:
        break
    }
  }

  return {
    messages: [],
    status: 'idle',
    streaming: '',
    chart: null,
    toolCalls: [],
    approval: null,
    metrics: null,
    pendingFile: null,
    pendingTaskId: null,

    async loadMessages(sessionId) {
      const items = await sessionApi.messages(sessionId)
      set({
        messages: items.map((item) => ({ ...item, chart: null, file: null })),
        status: 'idle',
        streaming: '',
        chart: null,
        toolCalls: [],
        metrics: null,
        pendingFile: null,
        pendingTaskId: null,
      })
    },

    async send(sessionId, text) {
      const token = localStorage.getItem('insight_token') ?? ''
      set((state) => ({
        messages: [
          ...state.messages,
          { role: 'user', content: text, createdAt: new Date().toISOString() },
        ],
        status: 'running',
        streaming: '',
        chart: null,
        toolCalls: [],
        approval: null,
        metrics: null,
        pendingFile: null,
        pendingTaskId: null,
      }))
      const task = await taskApi.create({ sessionId, message: text })
      set({ pendingTaskId: task.taskId })
      connectTaskEvents(task.taskId, token, {
        onEvent: handleEvent,
        onError: () => set({ status: 'error' }),
      })
    },

    async resolveApproval(approved) {
      const approval = useChatStore.getState().approval
      if (!approval) {
        return
      }
      await taskApi.approve(approval.taskId, approved, '')
      set({ approval: null, status: approved ? 'running' : 'done' })
    },

    clear() {
      set({
        messages: [],
        status: 'idle',
        streaming: '',
        chart: null,
        toolCalls: [],
        approval: null,
        metrics: null,
        pendingFile: null,
        pendingTaskId: null,
      })
    },
  }
})