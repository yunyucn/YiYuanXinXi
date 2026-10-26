<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import { reportApi } from '@/api'
import { useAppStore } from '@/store/app'
import { chartColors, chartSplitColor, chartTextColor, disposeCharts, initChart } from '@/utils/echarts'
import { addDays, downloadBlob, formatDate, todayString } from '@/utils/format'

const appStore = useAppStore()
const today = todayString()
const range = ref([addDays(today, -29), today])
const loading = ref(false)
const exporting = ref(false)
const report = ref(null)
const trendRef = ref(null)
const typeRef = ref(null)
const deptRef = ref(null)
const adverseRef = ref(null)
const charts = { trend: null, type: null, dept: null, adverse: null }

const cards = computed(() => {
  const data = report.value?.cards || {}
  return [
    { label: '入库袋数', value: data.inbound ?? 0, unit: '袋', hint: '统计区间内新增入库' },
    { label: '出库袋数', value: data.outbound ?? 0, unit: '袋', hint: '按发血记录统计' },
    { label: '报废袋数', value: data.scrapped ?? 0, unit: '袋', hint: `报废率 ${data.scrap_rate ?? 0}%` },
    { label: '当前库存', value: data.ending_stock ?? 0, unit: '袋', hint: '当前在库血袋总数' },
  ]
})

const trendRows = computed(() => report.value?.trend || [])

function renderCharts() {
  if (!report.value) return
  const textColor = chartTextColor(appStore.dark)
  const splitColor = chartSplitColor(appStore.dark)
  const borderColor = appStore.dark ? '#263449' : '#ffffff'
  const trend = report.value.trend || []

  if (trendRef.value) {
    if (!charts.trend) charts.trend = initChart(trendRef.value)
    charts.trend.setOption(
      {
        animationDuration: 500,
        color: ['#059669', '#2563EB'],
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { color: textColor, fontSize: 11 } },
        grid: { left: 42, right: 18, top: 34, bottom: 30 },
        xAxis: {
          type: 'category',
          data: trend.map((item) => item.date.slice(5)),
          axisLabel: { color: textColor, fontSize: 10 },
          axisLine: { lineStyle: { color: splitColor } },
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: textColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitColor } },
        },
        series: [
          { name: '入库', type: 'bar', barMaxWidth: 18, data: trend.map((item) => item.inbound_bags) },
          { name: '出库', type: 'bar', barMaxWidth: 18, data: trend.map((item) => item.outbound_bags) },
        ],
      },
      true,
    )
  }

  if (typeRef.value) {
    if (!charts.type) charts.type = initChart(typeRef.value)
    charts.type.setOption(
      {
        animationDuration: 500,
        color: chartColors,
        tooltip: { trigger: 'item', formatter: '{b} 型：{c} 袋（{d}%）' },
        legend: { bottom: 0, textStyle: { color: textColor, fontSize: 10 } },
        series: [
          {
            type: 'pie',
            radius: ['44%', '67%'],
            center: ['50%', '43%'],
            label: { show: false },
            itemStyle: { borderColor, borderWidth: 3 },
            data: report.value.blood_type_stock || [],
          },
        ],
      },
      true,
    )
  }

  if (deptRef.value) {
    if (!charts.dept) charts.dept = initChart(deptRef.value)
    const department = report.value.department_usage || []
    charts.dept.setOption(
      {
        animationDuration: 500,
        color: ['#2563EB'],
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 82, right: 22, top: 16, bottom: 28 },
        xAxis: {
          type: 'value',
          axisLabel: { color: textColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitColor } },
        },
        yAxis: {
          type: 'category',
          data: department.map((item) => item.name),
          axisLabel: { color: textColor, fontSize: 10 },
          axisLine: { lineStyle: { color: splitColor } },
        },
        series: [{ type: 'bar', barMaxWidth: 18, data: department.map((item) => item.value), itemStyle: { borderRadius: [0, 3, 3, 0] } }],
      },
      true,
    )
  }

  if (adverseRef.value) {
    if (!charts.adverse) charts.adverse = initChart(adverseRef.value)
    charts.adverse.setOption(
      {
        animationDuration: 500,
        color: ['#D97706', '#DC2626', '#7C3AED', '#64748B'],
        tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
        legend: { bottom: 0, textStyle: { color: textColor, fontSize: 10 } },
        series: [
          {
            type: 'pie',
            radius: ['44%', '67%'],
            center: ['50%', '43%'],
            label: { show: false },
            itemStyle: { borderColor, borderWidth: 3 },
            data: report.value.adverse_distribution || [],
          },
        ],
      },
      true,
    )
  }
}

async function loadReport() {
  if (!range.value?.length) {
    ElMessage.warning('请选择统计日期范围')
    return
  }
  loading.value = true
  try {
    report.value = await reportApi.overview({ start_date: range.value[0], end_date: range.value[1] })
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  if (!range.value?.length) return
  exporting.value = true
  try {
    const blob = await reportApi.exportCsv({ start_date: range.value[0], end_date: range.value[1] })
    downloadBlob(blob, `bloodbank-report-${range.value[0]}-${range.value[1]}.csv`)
    ElMessage.success('报表已导出为 CSV')
  } finally {
    exporting.value = false
  }
}

function resizeCharts() {
  Object.values(charts).forEach((chart) => chart?.resize())
}

onMounted(() => {
  loadReport()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts(Object.values(charts))
})

watch(() => appStore.dark, () => nextTick(renderCharts))
</script>

<template>
  <div class="page">
    <PageHeader title="统计报表" description="按日期范围统计出入库、报废、血型库存、科室用血与不良反应分布">
      <template #actions>
        <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" style="width: 260px" />
        <el-button :icon="Refresh" :loading="loading" @click="loadReport">查询</el-button>
        <el-button type="primary" :icon="Download" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
      </template>
    </PageHeader>

    <div v-loading="loading">
      <div class="stat-grid report-cards">
        <div v-for="card in cards" :key="card.label" class="stat-card">
          <div class="label">{{ card.label }}</div>
          <div class="value">{{ card.value }}<small>{{ card.unit }}</small></div>
          <div class="hint">{{ card.hint }}</div>
        </div>
      </div>

      <div class="chart-grid">
        <section class="page-card chart-card wide">
          <div class="chart-head"><h3>每日出入库趋势</h3><span>{{ report?.range?.start_date }} 至 {{ report?.range?.end_date }}</span></div>
          <div ref="trendRef" class="chart" />
        </section>
        <section class="page-card chart-card">
          <div class="chart-head"><h3>血型库存占比</h3><span>当前在库</span></div>
          <div ref="typeRef" class="chart" />
        </section>
        <section class="page-card chart-card">
          <div class="chart-head"><h3>科室用血分布</h3><span>按发放量统计</span></div>
          <div ref="deptRef" class="chart" />
        </section>
        <section class="page-card chart-card">
          <div class="chart-head"><h3>不良反应类型</h3><span>统计区间内上报</span></div>
          <div ref="adverseRef" class="chart" />
        </section>
      </div>

      <section class="page-card daily-table">
        <div class="chart-head"><h3>每日统计明细</h3><span>共 {{ trendRows.length }} 天</span></div>
        <el-table :data="trendRows" border max-height="330" size="small">
          <el-table-column label="日期" min-width="120">
            <template #default="{ row }">{{ formatDate(row.date) }}</template>
          </el-table-column>
          <el-table-column prop="inbound_bags" label="入库袋数" min-width="100" align="right" />
          <el-table-column prop="inbound_quantity" label="入库量" min-width="100" align="right" />
          <el-table-column prop="outbound_bags" label="出库袋数" min-width="100" align="right" />
          <el-table-column prop="outbound_quantity" label="出库量" min-width="100" align="right" />
          <el-table-column prop="scrapped" label="报废袋数" min-width="100" align="right" />
          <el-table-column prop="ending_stock" label="期末库存" min-width="100" align="right" />
        </el-table>
      </section>
    </div>
  </div>
</template>

<style scoped>
.report-cards .value small {
  margin-left: 4px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.chart-card {
  min-height: 330px;
}

.chart-card.wide {
  grid-column: 1 / -1;
}

.chart-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--bb-border);
}

.chart-head h3 {
  margin: 0;
  font-size: 14px;
}

.chart-head span {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.chart {
  width: 100%;
  height: 250px;
  margin-top: 8px;
}

.daily-table {
  margin-top: 16px;
}

.daily-table .el-table {
  margin-top: 12px;
}
</style>
