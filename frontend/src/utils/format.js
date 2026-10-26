export function formatDate(value) {
  if (!value) return '-'
  return String(value).slice(0, 10)
}

export function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

export function formatTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(11, 19)
}

export function todayString() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

export function addDays(value, days) {
  if (!value) return '-'
  const date = new Date(`${value}T00:00:00`)
  date.setDate(date.getDate() + Number(days || 0))
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

export function daysBetween(value) {
  if (!value) return 0
  const target = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  const today = new Date(`${todayString()}T00:00:00`)
  return Math.round((target - today) / 86400000)
}

export const statusTypeMap = {
  在库: 'success',
  备血锁定: 'warning',
  已发血: 'primary',
  已报废: 'info',
  已过期: 'danger',
  待配血: 'warning',
  配血中: 'primary',
  已备血: 'success',
  已完成: 'success',
  已取消: 'info',
  待执行: 'warning',
  待审批: 'warning',
  已批准: 'success',
  已驳回: 'danger',
}

export function statusType(status) {
  return statusTypeMap[status] || 'info'
}

export function severityType(severity) {
  return { 轻度: 'warning', 中度: 'danger', 重度: 'danger' }[severity] || 'info'
}

export function urgencyType(urgency) {
  return { 常规: 'info', 紧急: 'warning', 抢救: 'danger' }[urgency] || 'info'
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
