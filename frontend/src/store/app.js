import { defineStore } from 'pinia'
import { alertApi } from '@/api'

export const useAppStore = defineStore('app', {
  state: () => ({
    collapsed: localStorage.getItem('bloodbank_sidebar') === 'collapsed',
    dark: localStorage.getItem('bloodbank_theme') === 'dark',
    alertCount: 0,
    latestAlerts: [],
    bellBounce: false,
  }),
  actions: {
    toggleSidebar() {
      this.collapsed = !this.collapsed
      localStorage.setItem('bloodbank_sidebar', this.collapsed ? 'collapsed' : 'expanded')
    },
    applyTheme() {
      document.documentElement.classList.toggle('dark', this.dark)
    },
    toggleTheme() {
      this.dark = !this.dark
      localStorage.setItem('bloodbank_theme', this.dark ? 'dark' : 'light')
      this.applyTheme()
    },
    async fetchAlertSummary(bounce = false) {
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
        this.alertCount = 0
      }
    },
  },
})
