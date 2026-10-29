/**
 * 按业务域封装后端 API，页面不直接拼接 URL。
 *
 * 每个方法均为薄封装，统一复用 Axios 的 JWT、错误提示与响应解包逻辑。
 */

import request from './request'

/** 认证与会话接口。 */
export const authApi = {
  login: (data) => request.post('/auth/login', data),
  me: () => request.get('/auth/me'),
  logout: () => request.post('/auth/logout'),
}

/** 首页统计接口。 */
export const dashboardApi = {
  summary: () => request.get('/dashboard/summary'),
}

/** 血袋入库、库存与储血设备接口。 */
export const bagApi = {
  list: (params) => request.get('/blood-bags', { params }),
  detail: (id) => request.get(`/blood-bags/${id}`),
  create: (data) => request.post('/blood-bags', data),
  createBatch: (data) => request.post('/blood-bags/batch', data),
  fridgeOverview: () => request.get('/stock/fridges'),
}

/** 输血申请接口。 */
export const requestApi = {
  list: (params) => request.get('/requests', { params }),
  detail: (id) => request.get(`/requests/${id}`),
  create: (data) => request.post('/requests', data),
  cancel: (id, data) => request.post(`/requests/${id}/cancel`, data),
  startMatch: (id) => request.post(`/requests/${id}/start-match`),
  recommendations: (id) => request.get(`/requests/${id}/recommendations`),
}

/** 配血工作台接口。 */
export const crossMatchApi = {
  pending: () => request.get('/cross-match/pending'),
  list: (params) => request.get('/cross-matches', { params }),
  create: (data) => request.post('/cross-matches', data),
  cancel: (data) => request.post('/cross-matches/cancel', data),
}

/** 发血与执行接口。 */
export const issueApi = {
  pending: () => request.get('/issues/pending'),
  list: (params) => request.get('/issues', { params }),
  detail: (id) => request.get(`/issues/${id}`),
  create: (data) => request.post('/issues', data),
  execute: (id) => request.post(`/issues/${id}/execute`),
}

/** 不良反应接口。 */
export const adverseApi = {
  list: (params) => request.get('/adverse-reactions', { params }),
  detail: (id) => request.get(`/adverse-reactions/${id}`),
  create: (data) => request.post('/adverse-reactions', data),
}

/** 患者全流程追溯接口。 */
export const traceApi = {
  get: (admissionNo) => request.get(`/trace/${encodeURIComponent(admissionNo)}`),
}

/** 预警中心接口。 */
export const alertApi = {
  list: (params) => request.get('/alerts', { params }),
  summary: () => request.get('/alerts/summary'),
  refresh: () => request.post('/alerts/refresh'),
  handle: (id, data) => request.post(`/alerts/${id}/handle`, data),
  scanLogs: () => request.get('/scan-logs'),
}

/** 报废申请与审批接口。 */
export const scrapApi = {
  list: (params) => request.get('/scraps', { params }),
  create: (data) => request.post('/scraps', data),
  expiredBatch: () => request.post('/scraps/expired-batch'),
  approve: (id, data) => request.post(`/scraps/${id}/approve`, data),
  reject: (id, data) => request.post(`/scraps/${id}/reject`, data),
}

/** 主任端统计报表接口。 */
export const reportApi = {
  overview: (params) => request.get('/reports/overview', { params }),
  exportCsv: (params) => request.get('/reports/export', { params, responseType: 'blob' }),
}

/** 系统管理接口。 */
export const systemApi = {
  products: () => request.get('/system/products'),
  fridges: () => request.get('/system/fridges'),
  departments: () => request.get('/system/departments'),
  roles: () => request.get('/system/roles'),
  users: () => request.get('/system/users'),
  logs: (params) => request.get('/system/logs', { params }),
  logDetail: (id) => request.get(`/system/logs/${id}`),
  createUser: (data) => request.post('/system/users', data),
  updateUser: (id, data) => request.put(`/system/users/${id}`, data),
  createDepartment: (data) => request.post('/system/departments', data),
  createProduct: (data) => request.post('/system/products', data),
  updateProduct: (id, data) => request.put(`/system/products/${id}`, data),
  createFridge: (data) => request.post('/system/fridges', data),
  updateFridge: (id, data) => request.put(`/system/fridges/${id}`, data),
}
