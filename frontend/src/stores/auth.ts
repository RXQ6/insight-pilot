import { create } from 'zustand'
import { authApi } from '../api/auth'
import type { User } from '../types'

interface AuthState {
  token: string | null
  user: User | null
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('insight_token'),
  user: null,
  async login(username, password) {
    const { data } = await authApi.login({ username, password })
    localStorage.setItem('insight_token', data.token)
    set({ token: data.token, user: data.user })
  },
  async register(username, password) {
    await authApi.register({ username, password })
  },
  logout() {
    localStorage.removeItem('insight_token')
    set({ token: null, user: null })
  },
}))
