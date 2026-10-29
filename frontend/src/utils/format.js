/** 通用日期、状态和文件下载格式化工具。 */

/**
 * 格式化日期为 `YYYY-MM-DD`。
 * @param {string} value ISO 日期字符串
 * @returns {string} 日期文本，空值返回短横线
 */
export function formatDate(value) {
  if (!value) return '-'
  return String(value).slice(0, 10)
}

/**
 * 格式化日期时间，保留到秒。
 * @param {string} value ISO 日期时间字符串
 * @returns {string} `YYYY-MM-DD HH:mm:ss`
 */
export function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

/**
 * 仅提取时间部分。
 * @param {string} value ISO 日期时间字符串
 * @returns {string} `HH:mm:ss`
 */
export function formatTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(11, 19)
}

/** 返回本地时区的今日日期字符串。 */
export function todayString() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

/**
 * 在指定日期上增加天数。
 * @param {string} value 起始日期
 * @param {number} days 增加天数，可为负数
 * @returns {string} 计算后的日期
 */
export function addDays(value, days) {
  if (!value) return '-'
  const date = new Date(`${value}T00:00:00`)
  date.setDate(date.getDate() + Number(days || 0))
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 10)
}

/**
 * 计算目标日期距今天数。
 * @param {string} value 目标日期
 * @returns {number} 剩余天数，负值表示已过期
 */
export function daysBetween(value) {
  if (!value) return 0
  const target = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  const today = new Date(`${todayString()}T00:00:00`)
  return Math.round((target - today) / 86400000)
}

/** 业务状态到 Element Plus 标签类型的映射。 */
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

/** 返回业务状态对应的标签类型。 */
export function statusType(status) {
  return statusTypeMap[status] || 'info'
}

/** 返回不良反应程度对应的标签类型。 */
export function severityType(severity) {
  return { 轻度: 'warning', 中度: 'danger', 重度: 'danger' }[severity] || 'info'
}

/** 返回申请紧急程度对应的标签类型。 */
export function urgencyType(urgency) {
  return { 常规: 'info', 紧急: 'warning', 抢救: 'danger' }[urgency] || 'info'
}

/**
 * 触发浏览器下载 Blob 文件，并释放临时对象 URL。
 * @param {Blob} blob 文件内容
 * @param {string} filename 下载文件名
 */
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
