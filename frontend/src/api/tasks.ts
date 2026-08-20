import { api } from './client'
import type { Task } from '../types'

export const taskApi = {
  create: (payload: { sessionId: number; message: string }) =>
    api.post<Task>('/tasks', payload).then((r) => r.data),
  get: (taskId: string) => api.get<Task>(`/tasks/${taskId}`).then((r) => r.data),
  trace: (taskId: string) =>
    api.get<{ taskId: string; steps: unknown[] }>(`/tasks/${taskId}/trace`).then((r) => r.data),
  approve: (taskId: string, approved: boolean, note: string) =>
    api.post<Task>(`/tasks/${taskId}/approve`, { approved, note }).then((r) => r.data),
  feedback: (taskId: string, helpful: boolean, comment?: string) =>
    api
      .post<{ recorded: boolean }>(`/tasks/${taskId}/feedback`, { helpful, comment: comment ?? '' })
      .then((r) => r.data),
}
