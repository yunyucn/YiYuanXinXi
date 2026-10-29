<script setup>
/**
 * 患者全周期追溯：按住院号聚合申请、配血、发血、执行和不良反应事件。
 *
 * 可追溯范围由后端按角色收敛：输血科/主任为全院，医生为本人开具申请的患者，
 * 护士为本人经手（执行/领血/上报不良反应）的患者。页面先加载“可追溯患者”清单，再按住院号
 * 展示闭环时间轴，避免不同角色进入后都看到同一份数据。
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Connection, Document, FirstAidKit, Refresh, Search, Warning } from '@element-plus/icons-vue'
import { traceApi } from '@/api'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const admissionNo = ref(String(route.query.admission_no || ''))
const loading = ref(false)
const searched = ref(false)
const result = ref(null)
const patients = ref([])
const patientsLoading = ref(false)
const scopeLabel = ref('')
const scopeCode = ref('')
const errorTip = ref('')

const eventMeta = {
  request: { label: '申请', icon: Document },
  cross_match: { label: '配血', icon: Connection },
  issue: { label: '发血', icon: FirstAidKit },
  execution: { label: '执行', icon: CircleCheck },
  adverse: { label: '不良反应', icon: Warning },
}

/** 追溯范围提示，随后端返回的角色范围变化。 */
const scopeHint = computed(() => {
  const scope = result.value?.scope || scopeCode.value
  if (scope === 'doctor') return '仅可查看本人开具申请的患者的输血记录，跨范围查询会被拒绝'
  if (scope === 'nurse') return '仅可查看本人执行、领血或上报不良反应的患者的输血记录，跨范围查询会被拒绝'
  if (scope === 'all') return '可查询全院患者的输血记录'
  return '请从上方可追溯患者中选择，或输入范围内的住院号'
})

/** 追溯统计摘要。 */
const summary = computed(() => result.value?.summary || { request_count: 0, bag_count: 0, adverse_count: 0 })
/** 按时间升序排列的追溯事件。 */
const events = computed(() => result.value?.events || [])

/** 加载当前角色可追溯的患者清单。 */
async function loadPatients() {
  patientsLoading.value = true
  try {
    const data = await traceApi.patients()
    patients.value = data.items || []
    scopeLabel.value = data.scope_label || ''
    scopeCode.value = data.scope || ''
  } catch {
    patients.value = []
  } finally {
    patientsLoading.value = false
  }
}

/** 校验住院号、加载追溯数据并同步地址栏查询参数，超出范围时清空结果。 */
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
    errorTip.value = ''
    router.replace({ query: { admission_no: value } })
  } catch {
    // 越权或不存在时清空链路，提示弹窗由请求拦截器统一弹出
    result.value = null
    errorTip.value = '该住院号不在当前角色的追溯范围内，或不存在输血记录'
  } finally {
    loading.value = false
  }
}

/** 选择可追溯患者后加载其闭环链路。 */
function selectPatient(item) {
  admissionNo.value = item.admission_no
  loadTrace()
}

/** 过滤事件详情中的空值，生成键值展示列表。 */
function detailEntries(detail) {
  return Object.entries(detail || {}).filter(([, value]) => value !== null && value !== undefined && value !== '')
}

onMounted(async () => {
  await loadPatients()
  if (admissionNo.value) {
    await loadTrace()
  } else if (patients.value.length) {
    await selectPatient(patients.value[0])
  }
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="全周期输血追溯"
      :description="scopeLabel ? `追溯范围：${scopeLabel}` : '输入住院号，串联输血申请、配血、发血、执行与不良反应全过程'"
    >
      <template #actions>
        <el-button :icon="Refresh" :loading="patientsLoading" @click="loadPatients">刷新范围</el-button>
      </template>
    </PageHeader>

    <section class="page-card picker-card">
      <div class="picker-head">
        <div>
          <h3>可追溯患者</h3>
          <p>{{ scopeLabel || '按当前角色加载' }} · 共 {{ patients.length }} 位患者，点击卡片查看闭环链路</p>
        </div>
      </div>
      <div v-loading="patientsLoading" class="patient-picker">
        <button
          v-for="item in patients"
          :key="item.admission_no"
          type="button"
          class="patient-chip"
          :class="{ active: item.admission_no === admissionNo }"
          @click="selectPatient(item)"
        >
          <span class="chip-name">{{ item.patient_name }}</span>
          <span class="chip-meta">{{ item.admission_no }} · {{ item.department }} {{ item.bed_no || '' }}</span>
          <span class="chip-foot">{{ item.blood_type }}{{ item.rh }} · 申请 {{ item.request_count }} 张</span>
        </button>
        <div v-if="!patientsLoading && !patients.length" class="chip-empty">
          当前角色暂无可追溯的住院患者
        </div>
      </div>
    </section>

    <section class="page-card search-card">
      <div class="search-box">
        <div>
          <label>患者住院号</label>
          <el-input v-model="admissionNo" size="large" :prefix-icon="Search" clearable placeholder="请输入住院号，如 ZY20240512005" @keyup.enter="loadTrace" />
        </div>
        <el-button type="primary" size="large" :loading="loading" @click="loadTrace">查询追溯链路</el-button>
      </div>
      <p>{{ scopeHint }}；追溯数据只读展示，红色节点为配血不相容，橙色节点为输血不良反应。</p>
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

      <section v-else-if="searched" class="page-card empty-state">
        <el-empty :image-size="110" :description="errorTip || '未找到该住院号的输血记录'">
          <el-button v-if="patients.length" type="primary" @click="selectPatient(patients[0])">查看范围内最近患者</el-button>
        </el-empty>
      </section>

      <section v-else class="page-card empty-state">
      <el-empty :image-size="110" description="从上方可追溯患者中选择，或输入住院号开始追溯" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.picker-card {
  margin-bottom: 16px;
}

.picker-head h3 {
  margin: 0;
  font-size: 14px;
}

.picker-head p {
  margin: 4px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.patient-picker {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 10px;
  min-height: 66px;
  margin-top: 12px;
}

.patient-chip {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  font: inherit;
  text-align: left;
  cursor: pointer;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-left: 3px solid var(--bb-primary);
  border-radius: 5px;
  transition: background 150ms, box-shadow 150ms, transform 150ms;
}

.patient-chip:hover {
  background: var(--bb-hover);
  box-shadow: var(--bb-shadow);
  transform: translateY(-1px);
}

.patient-chip.active {
  background: #eff6ff;
  border-color: var(--bb-primary);
  box-shadow: 0 0 0 1px var(--bb-primary) inset;
}

.chip-name {
  color: var(--bb-text);
  font-size: 14px;
  font-weight: 600;
}

.chip-meta,
.chip-foot {
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.chip-empty {
  grid-column: 1 / -1;
  padding: 14px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  text-align: center;
  background: var(--bb-hover);
  border: 1px dashed var(--bb-border);
  border-radius: 5px;
}

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
