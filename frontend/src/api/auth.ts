import { api } from './client'
import type { User } from '../types'

export const authApi = {
  register: (data: { username: string; password: string }) =>
    api.post<User>('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    api.post<{ token: string; expiresIn: number; user: User }>('/auth/login', data),
  me: () => api.get<User>('/auth/me'),
}
