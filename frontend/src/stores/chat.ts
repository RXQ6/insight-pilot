import { create } from 'zustand'
import { connectTaskEvents } from '../api/sse'
import { sessionApi } from '../api/sessions'
import { taskApi } from '../api/tasks'
import type { ChartSpec, Message, TaskEvent, TaskOutput, ToolCallEvent } from '../types'

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
      case 'tool_call':
        set((state) => ({
          toolCalls: [
            ...state.toolCalls,
            {
              name: event.tool ?? event.args?.name,
              arguments: event.args,
              status: 'running',
            } as ToolCallEvent,
          ],
        }))
        break
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
      case 'approval_required':
        set({
          approval: {
            taskId: event.taskId ?? '',
            reason: typeof content === 'string' ? content : '需要人工确认',
          },
        })
        break
      case 'result': {
        const output = (event.output ?? content) as TaskOutput | null
        set((state) => ({
          messages: [
            ...state.messages,
            {
              role: 'assistant',
              content: output?.answer ?? '已完成分析',
              chart: output?.chartSpec ?? null,
              createdAt: new Date().toISOString(),
            },
          ],
          streaming: '',
        }))
        break
      }
      case 'done':
        set({ status: 'done' })
        break
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

    async loadMessages(sessionId) {
      const items = await sessionApi.messages(sessionId)
      set({
        messages: items.map((item) => ({ ...item, chart: null })),
        status: 'idle',
        streaming: '',
        chart: null,
        toolCalls: [],
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
      }))
      const task = await taskApi.create({ sessionId, message: text })
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
      })
    },
  }
})
