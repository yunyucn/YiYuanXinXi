import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

service.interceptors.request.use((config) => {
  const token = localStorage.getItem('bloodbank_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

service.interceptors.response.use(
  (response) => {
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
