/**
 * 前端页面与操作的角色权限矩阵。
 *
 * 后端会再次执行同样的权限校验，前端矩阵只用于隐藏菜单、控制按钮可用性，
 * 不能作为安全边界。`admin` 由 `hasAnyRole` 统一放行全部权限。
 */
export const ACCESS = Object.freeze({
  dashboard: Object.freeze(['admin', 'tech', 'doctor', 'nurse', 'director']),
  bloodIn: Object.freeze(['tech']),
  stockView: Object.freeze(['tech', 'nurse', 'director']),
  stockOperate: Object.freeze(['tech']),
  requestView: Object.freeze(['doctor', 'tech', 'director']),
  requestCreate: Object.freeze(['doctor']),
  crossMatch: Object.freeze(['tech']),
  issue: Object.freeze(['tech']),
  execute: Object.freeze(['nurse']),
  trace: Object.freeze(['doctor', 'nurse', 'tech', 'director']),
  alerts: Object.freeze(['tech', 'director']),
  alertsHandle: Object.freeze(['tech']),
  adverse: Object.freeze(['nurse', 'tech', 'director']),
  scrapView: Object.freeze(['tech', 'director']),
  scrapApply: Object.freeze(['tech']),
  scrapApprove: Object.freeze(['director']),
  report: Object.freeze(['director']),
  system: Object.freeze(['admin']),
  print: Object.freeze(['tech', 'nurse', 'director']),
})

/**
 * 判断当前角色是否命中允许角色列表。
 * @param {string} role 当前用户角色编码
 * @param {string[]} roles 允许访问的角色编码
 * @returns {boolean} 是否允许访问；admin 始终返回 true
 */
export function hasAnyRole(role, roles) {
  if (role === 'admin') return true
  return Boolean(role) && Array.isArray(roles) && roles.includes(role)
}
