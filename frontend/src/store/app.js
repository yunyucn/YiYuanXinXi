/**
 * 全局界面状态：侧栏、主题和预警角标。
 *
 * 预警摘要只对具备预警权限的角色拉取，避免无权限页面出现待办提示。
 */

import { defineStore } from 'pinia'
import { alertApi } from '@/api'
import { ACCESS, hasAnyRole } from '@/constants/access'
import { useAuthStore } from '@/store/auth'

export const useAppStore = defineStore('app', {
  state: () => ({
    collapsed: localStorage.getItem('bloodbank_sidebar') === 'collapsed',
    dark: localStorage.getItem('bloodbank_theme') === 'dark',
    alertCount: 0,
    latestAlerts: [],
    bellBounce: false,
  }),
  actions: {
    /** 切换侧栏折叠状态并持久化。 */
    toggleSidebar() {
      this.collapsed = !this.collapsed
      localStorage.setItem('bloodbank_sidebar', this.collapsed ? 'collapsed' : 'expanded')
    },
    /** 将当前主题应用到根节点。 */
    applyTheme() {
      document.documentElement.classList.toggle('dark', this.dark)
    },
    /** 切换明暗主题并持久化。 */
    toggleTheme() {
      this.dark = !this.dark
      localStorage.setItem('bloodbank_theme', this.dark ? 'dark' : 'light')
      this.applyTheme()
    },
    /** 清空预警角标和摘要。 */
    clearAlertSummary() {
      this.alertCount = 0
      this.latestAlerts = []
      this.bellBounce = false
    },
    /** 拉取预警摘要；无预警权限时主动清空角标。 */
    async fetchAlertSummary(bounce = false) {
      const auth = useAuthStore()
      if (!auth.user || !hasAnyRole(auth.role, ACCESS.alerts)) {
        this.clearAlertSummary()
        return
      }
      try {
        const data = await alertApi.summary()
        this.alertCount = data.red_count
        this.latestAlerts = data.latest
        if (bounce) {
          this.bellBounce = true
          window.setTimeout(() => {
            this.bellBounce = false
          }, 420)
        }
      } catch {
        this.clearAlertSummary()
      }
    },
  },
})
