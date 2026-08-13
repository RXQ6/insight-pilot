export interface User {
  id: number
  username: string
  role: string
}

export interface Session {
  sessionId: number
  title: string
  messageCount: number
  updatedAt: string
}

export interface Message {
  role: 'user' | 'assistant' | 'tool'
  content: string
  taskId?: string | null
  chart?: ChartSpec | null
  createdAt: string
}

export interface ChartSpec {
  type: string
  title?: string
  xAxis?: (string | number)[]
  series?: (string | number)[]
}

export interface TaskOutput {
  answer?: string
  chartSpec?: ChartSpec | null
  sources?: string[]
}

export interface Task {
  taskId: string
  status: string
  output?: TaskOutput | null
  model?: string
  tokenIn?: number
  tokenOut?: number
  costCny?: number
  latencyMs?: number
  createdAt: string
  updatedAt: string
}

export interface ToolCallEvent {
  name?: string
  arguments?: Record<string, unknown>
  status?: string
  output?: string | null
}

export interface TaskEvent {
  type:
    | 'status'
    | 'tool_call'
    | 'token'
    | 'chart'
    | 'approval_required'
    | 'result'
    | 'done'
    | 'error'
  taskId?: string
  status?: string
  stage?: string
  content?: unknown
  tool?: string
  args?: Record<string, unknown>
  chartSpec?: ChartSpec
  output?: TaskOutput
  latencyMs?: number
  costCny?: number
  code?: string
  message?: string
  ts?: string
}

export interface EvalSummary {
  runId: string
  total: number
  passed: number
  sqlAccuracy: number
  avgCostCny: number
  finishedAt: string
}

export interface Dataset {
  id: number
  name: string
  tableName: string
  rowCount: number
  createdAt: string
}

export interface PreviewResponse {
  columns: string[]
  rows: Record<string, unknown>[]
}