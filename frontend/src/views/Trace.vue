<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Connection, Document, FirstAidKit, Search, Warning } from '@element-plus/icons-vue'
import { traceApi } from '@/api'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const admissionNo = ref(String(route.query.admission_no || 'ZY20240512005'))
const loading = ref(false)
const searched = ref(false)
const result = ref(null)

const demoNumbers = ['ZY20240512005', 'ZY20240512004', 'ZY20240512001']

const eventMeta = {
  request: { label: '申请', icon: Document },
  cross_match: { label: '配血', icon: Connection },
  issue: { label: '发血', icon: FirstAidKit },
  execution: { label: '执行', icon: CircleCheck },
  adverse: { label: '不良反应', icon: Warning },
}

const summary = computed(() => result.value?.summary || { request_count: 0, bag_count: 0, adverse_count: 0 })
const events = computed(() => result.value?.events || [])

async function loadTrace() {
  const value = admissionNo.value.trim()
  if (!value) {
    ElMessage.warning('请输入患者住院号')
    return
  }
  loading.value = true
  searched.value = true
  try {
    result.value = await traceApi.get(value)
    router.replace({ query: { admission_no: value } })
  } finally {
    loading.value = false
  }
}

function useDemo(value) {
  admissionNo.value = value
  loadTrace()
}

function detailEntries(detail) {
  return Object.entries(detail || {}).filter(([, value]) => value !== null && value !== undefined && value !== '')
}

onMounted(loadTrace)
</script>

<template>
  <div class="page">
    <PageHeader title="全周期输血追溯" description="输入住院号，串联输血申请、配血、发血、执行与不良反应全过程">
      <template #actions>
        <el-button v-for="item in demoNumbers" :key="item" size="small" @click="useDemo(item)">{{ item }}</el-button>
      </template>
    </PageHeader>

    <section class="page-card search-card">
      <div class="search-box">
        <div>
          <label>患者住院号</label>
          <el-input v-model="admissionNo" size="large" :prefix-icon="Search" clearable placeholder="请输入住院号，如 ZY20240512005" @keyup.enter="loadTrace" />
        </div>
        <el-button type="primary" size="large" :loading="loading" @click="loadTrace">查询追溯链路</el-button>
      </div>
      <p>追溯数据只读展示，包含不相容配血拦截记录；红色节点为配血不相容，橙色节点为输血不良反应。</p>
    </section>

    <div v-loading="loading" class="trace-content">
      <template v-if="result?.patient">
        <section class="page-card patient-card">
          <div class="patient-main">
            <div class="patient-avatar">{{ result.patient.name?.slice(0, 1) }}</div>
            <div>
              <span class="eyebrow">PATIENT TRACE · {{ result.admission_no }}</span>
              <h2>{{ result.patient.name }}</h2>
              <p>{{ result.patient.department }} · {{ result.patient.bed_no || '未填床号' }}</p>
            </div>
            <div class="blood-pair">
              <BloodBadge :type="result.patient.blood_type" :size="42" />
              <RhTag :rh="result.patient.rh" />
            </div>
          </div>
          <div class="summary-grid">
            <div><span>输血申请</span><strong>{{ summary.request_count }}</strong><small>张申请单</small></div>
            <div><span>发放血袋</span><strong>{{ summary.bag_count }}</strong><small>袋血液制品</small></div>
            <div><span>不良反应</span><strong class="warning-value">{{ summary.adverse_count }}</strong><small>条上报记录</small></div>
            <div><span>追溯节点</span><strong>{{ events.length }}</strong><small>个业务事件</small></div>
          </div>
        </section>

        <section class="page-card timeline-card">
          <div class="timeline-head">
            <div>
              <h3>输血闭环时间轴</h3>
              <p>按业务发生时间升序排列</p>
            </div>
            <span class="legend"><i class="danger" />不相容 <i class="warning" />不良反应 <i class="success" />已完成</span>
          </div>

          <div class="timeline">
            <article v-for="(event, index) in events" :key="event.id" class="timeline-item" :class="event.level">
              <div class="axis">
                <span class="node">
                  <el-icon :size="15"><component :is="eventMeta[event.event_type]?.icon || Document" /></el-icon>
                </span>
                <i v-if="index < events.length - 1" />
              </div>
              <div class="event-card">
                <div class="event-head">
                  <div>
                    <span class="event-type">{{ eventMeta[event.event_type]?.label || event.event_type }}</span>
                    <h3>{{ event.title }}</h3>
                  </div>
                  <time>{{ formatDateTime(event.time) }}</time>
                </div>
                <div v-if="event.request_no" class="request-ref">申请单 {{ event.request_no }}</div>
                <div class="event-detail">
                  <div v-for="[label, value] in detailEntries(event.detail)" :key="label">
                    <span>{{ label }}</span>
                    <strong>{{ value }}</strong>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>
      </template>

      <section v-else-if="searched && result" class="page-card empty-state">
        <el-empty :image-size="110" description="未找到该住院号的输血记录">
        <el-button type="primary" @click="useDemo('ZY20240512005')">查看示例追溯链路</el-button>
        </el-empty>
      </section>

      <section v-else class="page-card empty-state">
      <el-empty :image-size="110" description="输入住院号开始追溯，或点击右上角示例住院号" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.search-card {
  margin-bottom: 16px;
}

.search-box {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.search-box > div {
  flex: 1;
}

.search-box label {
  display: block;
  margin-bottom: 6px;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.search-card > p {
  margin: 10px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.trace-content {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 16px;
  min-height: 560px;
}

.patient-card {
  align-self: start;
}

.patient-main {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.patient-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  color: var(--bb-primary);
  font-size: 20px;
  font-weight: 700;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.eyebrow {
  color: var(--bb-primary);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.6px;
}

.patient-main h2 {
  margin: 5px 0 3px;
  font-size: 22px;
}

.patient-main p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.blood-pair {
  display: flex;
  grid-column: 1 / -1;
  gap: 8px;
  align-items: center;
  padding-top: 12px;
  margin-top: 4px;
  border-top: 1px dashed var(--bb-border);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin-top: 16px;
  overflow: hidden;
  background: var(--bb-border);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.summary-grid > div {
  padding: 12px;
  background: var(--bb-card);
}

.summary-grid span,
.summary-grid small {
  display: block;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.summary-grid strong {
  display: inline-block;
  margin: 6px 4px 4px 0;
  font-size: 24px;
  line-height: 1;
}

.summary-grid small {
  display: inline;
}

.warning-value {
  color: var(--bb-warning);
}

.timeline-card {
  min-width: 0;
}

.timeline-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--bb-border);
}

.timeline-head h3 {
  margin: 0;
  font-size: 15px;
}

.timeline-head p {
  margin: 4px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.legend {
  display: flex;
  gap: 6px;
  align-items: center;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.legend i {
  width: 7px;
  height: 7px;
  margin-left: 8px;
  background: var(--bb-primary);
  border-radius: 50%;
}

.legend i.danger {
  background: var(--bb-danger);
}

.legend i.warning {
  background: var(--bb-warning);
}

.legend i.success {
  background: var(--bb-success);
}

.timeline-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
}

.axis {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.axis i {
  flex: 1;
  width: 1px;
  min-height: 20px;
  background: var(--bb-border);
}

.node {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  color: #fff;
  background: var(--bb-primary);
  border: 3px solid var(--bb-card);
  border-radius: 50%;
  box-shadow: 0 0 0 1px #bfdbfe;
}

.timeline-item.success .node {
  background: var(--bb-success);
  box-shadow: 0 0 0 1px #a7f3d0;
}

.timeline-item.danger .node {
  background: var(--bb-danger);
  box-shadow: 0 0 0 1px #fecaca;
}

.timeline-item.warning .node {
  background: var(--bb-warning);
  box-shadow: 0 0 0 1px #fde68a;
}

.event-card {
  padding: 12px 14px;
  margin-bottom: 14px;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-left: 3px solid var(--bb-primary);
  border-radius: 5px;
  transition: background 150ms, box-shadow 150ms;
}

.event-card:hover {
  background: var(--bb-hover);
  box-shadow: var(--bb-shadow);
}

.timeline-item.success .event-card {
  border-left-color: var(--bb-success);
}

.timeline-item.danger .event-card {
  background: #fef2f2;
  border-left-color: var(--bb-danger);
}

.timeline-item.warning .event-card {
  background: #fffbeb;
  border-left-color: var(--bb-warning);
}

.event-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.event-type {
  color: var(--bb-text-secondary);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
}

.event-head h3 {
  margin: 3px 0 0;
  font-size: 14px;
}

.event-head time,
.request-ref {
  color: var(--bb-text-secondary);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.request-ref {
  margin-top: 5px;
  color: var(--bb-primary);
}

.event-detail {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 22px;
  padding-top: 9px;
  margin-top: 9px;
  border-top: 1px dashed var(--bb-border);
}

.event-detail > div {
  display: flex;
  gap: 8px;
  min-width: 0;
  font-size: 11px;
}

.event-detail span {
  flex: 0 0 72px;
  color: var(--bb-text-secondary);
}

.event-detail strong {
  min-width: 0;
  font-weight: 500;
  word-break: break-all;
}

.empty-state {
  grid-column: 1 / -1;
  min-height: 460px;
}

</style>
