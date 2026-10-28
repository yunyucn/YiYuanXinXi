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
  adverse: Object.freeze(['nurse', 'tech', 'director']),
  scrapView: Object.freeze(['tech', 'director']),
  scrapApply: Object.freeze(['tech']),
  scrapApprove: Object.freeze(['director']),
  report: Object.freeze(['director']),
  system: Object.freeze(['admin']),
  print: Object.freeze(['tech', 'nurse', 'director']),
})

export function hasAnyRole(role, roles) {
  if (role === 'admin') return true
  return Boolean(role) && Array.isArray(roles) && roles.includes(role)
}
