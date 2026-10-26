import { defineStore } from 'pinia'
import { authApi } from '@/api'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem('bloodbank_user') || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('bloodbank_token') || '',
    user: readUser(),
  }),
  getters: {
    role: (state) => state.user?.role || '',
    isLoggedIn: (state) => Boolean(state.token),
  },
  actions: {
    async login(payload) {
      const data = await authApi.login(payload)
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('bloodbank_token', this.token)
      localStorage.setItem('bloodbank_user', JSON.stringify(this.user))
      return data
    },
    async fetchMe() {
      const user = await authApi.me()
      this.user = user
      localStorage.setItem('bloodbank_user', JSON.stringify(user))
      return user
    },
    async logout() {
      try {
        await authApi.logout()
      } catch {
        // 本地退出不依赖服务端响应
      }
      this.token = ''
      this.user = null
      localStorage.removeItem('bloodbank_token')
      localStorage.removeItem('bloodbank_user')
    },
    hasRole(roles) {
      if (!roles || !roles.length) return true
      return this.role === 'admin' || roles.includes(this.role)
    },
  },
})
