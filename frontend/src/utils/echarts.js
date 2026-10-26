import * as echarts from 'echarts'

export const chartColors = ['#2563EB', '#059669', '#D97706', '#DC2626', '#7C3AED']

export function initChart(element) {
  return echarts.init(element)
}

export function disposeCharts(charts) {
  charts.forEach((chart) => chart && chart.dispose())
}

export function chartTextColor(dark) {
  return dark ? '#CBD5E1' : '#475569'
}

export function chartSplitColor(dark) {
  return dark ? '#334155' : '#E2E8F0'
}
