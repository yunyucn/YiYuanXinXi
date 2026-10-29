/**
 * 登录会话状态。
 *
 * 令牌和用户快照持久化到 localStorage，刷新页面后由路由守卫恢复会话；
 * 服务端仍是权限判断的最终依据。
 */

import { defineStore } from 'pinia'
import { authApi } from '@/api'
import { ACCESS, hasAnyRole } from '@/constants/access'

/** 安全读取本地用户快照，数据损坏时返回 null。 */
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
    /** 当前角色编码。 */
    role: (state) => state.user?.role || '',
    /** 是否存在本地访问令牌。 */
    isLoggedIn: (state) => Boolean(state.token),
    /** 判断当前用户是否拥有指定权限点。 */
    canAccess: (state) => (permission) => hasAnyRole(state.user?.role, ACCESS[permission]),
  },
  actions: {
    /** 登录成功后保存令牌与用户资料。 */
    async login(payload) {
      const data = await authApi.login(payload)
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('bloodbank_token', this.token)
      localStorage.setItem('bloodbank_user', JSON.stringify(this.user))
      return data
    },
    /** 从服务端刷新当前用户资料，并同步本地快照。 */
    async fetchMe() {
      const user = await authApi.me()
      this.user = user
      localStorage.setItem('bloodbank_user', JSON.stringify(user))
      return user
    },
    /** 退出登录并清理本地会话，服务端失败不阻塞本地退出。 */
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
    /** 判断当前角色是否属于指定角色集合。 */
    hasRole(roles) {
      if (!roles || !roles.length) return true
      return hasAnyRole(this.role, roles)
    },
  },
})
