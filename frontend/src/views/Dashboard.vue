<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Box, Clock, FirstAidKit, Warning } from '@element-plus/icons-vue'
import { dashboardApi } from '@/api'
import { useAppStore } from '@/store/app'
import { chartSplitColor, chartTextColor, disposeCharts, initChart } from '@/utils/echarts'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const appStore = useAppStore()
const loading = ref(false)
const summary = ref(null)
const trendRef = ref(null)
const typeRef = ref(null)
let trendChart = null
let typeChart = null

const cards = computed(() => {
  const data = summary.value?.cards || {}
  return [
    {
      key: 'in_stock',
      label: '在库血袋数',
      value: data.in_stock ?? 0,
      hint: '可调配库存，实时联动冰箱视图',
      icon: Box,
      tone: 'blue',
    },
    {
      key: 'pending_requests',
      label: '待配血申请',
      value: data.pending_requests ?? 0,
      hint: '含待配血与配血中申请单',
      icon: Clock,
      tone: 'amber',
    },
    {
      key: 'expiring',
      label: '临期血袋 ≤7 天',
      value: data.expiring ?? 0,
      hint: `其中 ${data.critical_expiring ?? 0} 袋 ≤3 天，需优先处理`,
      icon: Warning,
      tone: 'red',
    },
    {
      key: 'today_issued',
      label: '今日发血',
      value: data.today_issued ?? 0,
      hint: '今日已完成发血核对记录数',
      icon: FirstAidKit,
      tone: 'green',
    },
  ]
})

function levelClass(level) {
  return { 严重: 'danger', 警告: 'warning', 提示: 'info' }[level] || 'info'
}

function renderCharts() {
  if (!summary.value) return
  const dark = appStore.dark
  const textColor = chartTextColor(dark)
  const splitColor = chartSplitColor(dark)
  const trend = summary.value.trend || []
  const typeData = summary.value.blood_type_stock || []

  if (trendRef.value) {
    if (!trendChart) trendChart = initChart(trendRef.value)
    trendChart.setOption(
      {
        animationDuration: 500,
        grid: { left: 38, right: 18, top: 30, bottom: 28 },
        tooltip: { trigger: 'axis' },
        legend: { right: 0, top: 0, textStyle: { color: textColor, fontSize: 11 } },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: trend.map((item) => item.date.slice(5)),
          axisLine: { lineStyle: { color: splitColor } },
          axisLabel: { color: textColor, fontSize: 10 },
        },
        yAxis: {
          type: 'value',
          minInterval: 1,
          axisLabel: { color: textColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitColor } },
        },
        series: [
          {
            name: '入库',
            type: 'line',
            smooth: true,
            symbolSize: 6,
            data: trend.map((item) => item.inbound),
            lineStyle: { width: 2, color: '#059669' },
            itemStyle: { color: '#059669' },
            areaStyle: { color: 'rgba(5, 150, 105, 0.08)' },
          },
          {
            name: '出库',
            type: 'line',
            smooth: true,
            symbolSize: 6,
            data: trend.map((item) => item.outbound),
            lineStyle: { width: 2, color: '#2563EB' },
            itemStyle: { color: '#2563EB' },
            areaStyle: { color: 'rgba(37, 99, 235, 0.08)' },
          },
        ],
      },
      true,
    )
  }

  if (typeRef.value) {
    if (!typeChart) typeChart = initChart(typeRef.value)
    typeChart.setOption(
      {
        animationDuration: 500,
        tooltip: { trigger: 'item', formatter: '{b} 型：{c} 袋（{d}%）' },
        legend: { bottom: 0, textStyle: { color: textColor, fontSize: 11 } },
        color: ['#2563EB', '#D97706', '#7C3AED', '#059669'],
        series: [
          {
            type: 'pie',
            radius: ['50%', '70%'],
            center: ['50%', '44%'],
            avoidLabelOverlap: true,
            label: { show: false },
            itemStyle: { borderColor: dark ? '#263449' : '#fff', borderWidth: 3 },
            data: typeData,
          },
        ],
      },
      true,
    )
  }
}

async function loadData() {
  loading.value = true
  try {
    summary.value = await dashboardApi.summary()
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function resizeCharts() {
  trendChart?.resize()
  typeChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts([trendChart, typeChart])
})

watch(() => appStore.dark, () => nextTick(renderCharts))
</script>

<template>
  <div v-loading="loading" class="page">
    <PageHeader title="首页仪表盘" description="输血科运行概览 · 数据来源于入库、配血、发血与预警扫描">
      <template #actions>
        <el-button :loading="loading" @click="loadData">刷新数据</el-button>
      </template>
    </PageHeader>

    <div class="stat-grid">
      <div v-for="card in cards" :key="card.key" class="stat-card" :class="card.tone">
        <DecorPattern variant="cells" :tone="card.tone === 'red' ? 'rose' : card.tone" class="stat-decor" />
        <div class="label">
          <span class="stat-icon"><el-icon :size="18"><component :is="card.icon" /></el-icon></span>
          {{ card.label }}
        </div>
        <div class="value">{{ card.value }}</div>
        <div class="hint">{{ card.hint }}</div>
      </div>
    </div>

    <div class="chart-grid">
      <section class="page-card chart-card wide">
        <div class="card-head">
          <div>
            <h3>近 7 日出入库趋势</h3>
            <p>入库按创建时间统计，出库按发血时间统计</p>
          </div>
          <span class="legend-note"><i class="in" />入库 <i class="out" />出库</span>
        </div>
        <div ref="trendRef" class="chart" />
      </section>
      <section class="page-card chart-card">
        <div class="card-head">
          <div>
            <h3>血型库存占比</h3>
            <p>当前在库血袋按 ABO 血型分布</p>
          </div>
        </div>
        <div ref="typeRef" class="chart" />
      </section>
    </div>

    <section class="page-card alert-section">
      <div class="card-head">
        <div>
          <h3>预警待办</h3>
          <p>按严重程度排序，优先处理高风险预警</p>
        </div>
        <el-button text type="primary" @click="router.push('/alerts')">查看全部</el-button>
      </div>
      <div v-if="summary?.recent_alerts?.length" class="alert-list">
        <div v-for="item in summary.recent_alerts" :key="item.id" class="alert-row">
          <span class="alert-dot" :class="levelClass(item.level)" />
          <span class="alert-type">{{ item.type }}</span>
          <span class="alert-level" :class="levelClass(item.level)">{{ item.level }}</span>
          <p>{{ item.content }}</p>
          <span class="alert-time">{{ formatDateTime(item.created_at) }}</span>
          <el-button text type="primary" @click="router.push('/alerts')">去处理</el-button>
        </div>
      </div>
      <div v-else class="empty-alert">当前没有未处理预警，库存状态平稳。</div>
    </section>
  </div>
</template>

<style scoped>
.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card > *:not(.stat-decor) {
  position: relative;
  z-index: 1;
}

.stat-decor {
  right: 0;
  left: auto;
  width: 62%;
  opacity: 0.44;
  mask-image: linear-gradient(90deg, transparent 0%, #000 58%, #000 100%);
}

.stat-card::after {
  position: absolute;
  top: 0;
  right: 0;
  width: 3px;
  height: 100%;
  content: "";
  background: #2563eb;
}

.stat-card.amber::after {
  background: #d97706;
}

.stat-card.red::after {
  background: #dc2626;
}

.stat-card.green::after {
  background: #059669;
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: #2563eb;
  background: #eff6ff;
  border-radius: 5px;
}

.amber .stat-icon {
  color: #d97706;
  background: #fffbeb;
}

.red .stat-icon {
  color: #dc2626;
  background: #fef2f2;
}

.green .stat-icon {
  color: #059669;
  background: #ecfdf5;
}

.chart-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.chart-card {
  min-height: 350px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-head h3 {
  margin: 0;
  color: var(--bb-text);
  font-size: 15px;
}

.card-head p {
  margin: 4px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.legend-note {
  display: flex;
  gap: 6px;
  align-items: center;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.legend-note i {
  width: 14px;
  height: 3px;
  margin-left: 8px;
  border-radius: 2px;
}

.legend-note i.in {
  background: #059669;
}

.legend-note i.out {
  background: #2563eb;
}

.chart {
  width: 100%;
  height: 280px;
}

.alert-section {
  margin-top: 16px;
}

.alert-list {
  border-top: 1px solid var(--bb-border);
}

.alert-row {
  display: grid;
  grid-template-columns: 8px 68px 46px minmax(0, 1fr) 150px 56px;
  gap: 10px;
  align-items: center;
  min-height: 50px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--bb-border);
}

.alert-row:hover {
  background: var(--bb-hover);
}

.alert-dot {
  width: 7px;
  height: 7px;
  background: #2563eb;
  border-radius: 50%;
}

.alert-dot.warning {
  background: #d97706;
}

.alert-dot.danger {
  background: #dc2626;
}

.alert-type {
  color: var(--bb-text);
  font-size: 12px;
  font-weight: 600;
}

.alert-level {
  font-size: 11px;
  color: #2563eb;
}

.alert-level.warning {
  color: #d97706;
}

.alert-level.danger {
  color: #dc2626;
}

.alert-row p {
  margin: 0;
  overflow: hidden;
  color: var(--bb-text-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-time {
  color: var(--bb-text-secondary);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.empty-alert {
  padding: 32px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  text-align: center;
  border-top: 1px solid var(--bb-border);
}
</style>
