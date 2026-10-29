/** ECharts 初始化与主题色工具。 */

import * as echarts from 'echarts'

/** 系统图表统一配色。 */
export const chartColors = ['#2563EB', '#059669', '#D97706', '#DC2626', '#7C3AED']

/** 在指定 DOM 节点上初始化图表实例。 */
export function initChart(element) {
  return echarts.init(element)
}

/** 批量销毁图表，防止切换页面后实例泄漏。 */
export function disposeCharts(charts) {
  charts.forEach((chart) => chart && chart.dispose())
}

/** 返回适配明暗主题的图表文字颜色。 */
export function chartTextColor(dark) {
  return dark ? '#CBD5E1' : '#475569'
}

/** 返回适配明暗主题的坐标轴分隔线颜色。 */
export function chartSplitColor(dark) {
  return dark ? '#334155' : '#E2E8F0'
}
