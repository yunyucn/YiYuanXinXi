import request from './request'

export const authApi = {
  login: (data) => request.post('/auth/login', data),
  me: () => request.get('/auth/me'),
  logout: () => request.post('/auth/logout'),
}

export const dashboardApi = {
  summary: () => request.get('/dashboard/summary'),
}

export const bagApi = {
  list: (params) => request.get('/blood-bags', { params }),
  detail: (id) => request.get(`/blood-bags/${id}`),
  create: (data) => request.post('/blood-bags', data),
  createBatch: (data) => request.post('/blood-bags/batch', data),
  fridgeOverview: () => request.get('/stock/fridges'),
}

export const requestApi = {
  list: (params) => request.get('/requests', { params }),
  detail: (id) => request.get(`/requests/${id}`),
  create: (data) => request.post('/requests', data),
  cancel: (id, data) => request.post(`/requests/${id}/cancel`, data),
  startMatch: (id) => request.post(`/requests/${id}/start-match`),
  recommendations: (id) => request.get(`/requests/${id}/recommendations`),
}

export const crossMatchApi = {
  pending: () => request.get('/cross-match/pending'),
  list: (params) => request.get('/cross-matches', { params }),
  create: (data) => request.post('/cross-matches', data),
  cancel: (data) => request.post('/cross-matches/cancel', data),
}

export const issueApi = {
  pending: () => request.get('/issues/pending'),
  list: (params) => request.get('/issues', { params }),
  detail: (id) => request.get(`/issues/${id}`),
  create: (data) => request.post('/issues', data),
  execute: (id) => request.post(`/issues/${id}/execute`),
}

export const adverseApi = {
  list: (params) => request.get('/adverse-reactions', { params }),
  detail: (id) => request.get(`/adverse-reactions/${id}`),
  create: (data) => request.post('/adverse-reactions', data),
}

export const traceApi = {
  get: (admissionNo) => request.get(`/trace/${encodeURIComponent(admissionNo)}`),
}

export const alertApi = {
  list: (params) => request.get('/alerts', { params }),
  summary: () => request.get('/alerts/summary'),
  refresh: () => request.post('/alerts/refresh'),
  handle: (id, data) => request.post(`/alerts/${id}/handle`, data),
  scanLogs: () => request.get('/scan-logs'),
}

export const scrapApi = {
  list: (params) => request.get('/scraps', { params }),
  create: (data) => request.post('/scraps', data),
  expiredBatch: () => request.post('/scraps/expired-batch'),
  approve: (id, data) => request.post(`/scraps/${id}/approve`, data),
  reject: (id, data) => request.post(`/scraps/${id}/reject`, data),
}

export const reportApi = {
  overview: (params) => request.get('/reports/overview', { params }),
  exportCsv: (params) => request.get('/reports/export', { params, responseType: 'blob' }),
}

export const systemApi = {
  products: () => request.get('/system/products'),
  fridges: () => request.get('/system/fridges'),
  departments: () => request.get('/system/departments'),
  roles: () => request.get('/system/roles'),
  users: () => request.get('/system/users'),
  logs: (params) => request.get('/system/logs', { params }),
  createUser: (data) => request.post('/system/users', data),
  updateUser: (id, data) => request.put(`/system/users/${id}`, data),
  createDepartment: (data) => request.post('/system/departments', data),
  createProduct: (data) => request.post('/system/products', data),
  updateProduct: (id, data) => request.put(`/system/products/${id}`, data),
  createFridge: (data) => request.post('/system/fridges', data),
  updateFridge: (id, data) => request.put(`/system/fridges/${id}`, data),
}
