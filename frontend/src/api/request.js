/**
 * Axios 实例与全局请求拦截逻辑。
 *
 * 请求阶段自动附加 JWT；响应阶段解包统一业务响应，并在 401 时清理会话、
 * 跳转登录页。页面业务代码只需处理成功后的 `data`。
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 为每次请求附加本地保存的访问令牌。
service.interceptors.request.use((config) => {
  const token = localStorage.getItem('bloodbank_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

service.interceptors.response.use(
  (response) => {
    // 文件下载保留 Blob，其余接口统一解包 { code, msg, data }。
    if (response.config.responseType === 'blob') {
      return response.data
    }
    const payload = response.data
    if (payload && payload.code === 0) {
      return payload.data
    }
    const message = payload?.msg || '请求失败'
    ElMessage.error(message)
    return Promise.reject(new Error(message))
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.msg || error.message || '网络请求失败'
    if (status === 401) {
      // 令牌失效时清空本地会话，避免继续携带无效凭证。
      localStorage.removeItem('bloodbank_token')
      localStorage.removeItem('bloodbank_user')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default service
