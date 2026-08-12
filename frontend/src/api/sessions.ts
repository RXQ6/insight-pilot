import { api } from './client'
import type { Message, Session } from '../types'

export const sessionApi = {
  list: () => api.get<{ items: Session[] }>('/sessions').then((r) => r.data.items),
  create: (title: string) => api.post<Session>('/sessions', { title }).then((r) => r.data),
  messages: (sessionId: number) =>
    api.get<{ items: Message[] }>(`/sessions/${sessionId}/messages`).then((r) => r.data.items),
  remove: (sessionId: number) => api.delete(`/sessions/${sessionId}`),
}
