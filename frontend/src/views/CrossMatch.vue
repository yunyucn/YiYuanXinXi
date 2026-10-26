<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { crossMatchApi, requestApi } from '@/api'
import { formatDate, formatDateTime } from '@/utils/format'

const loading = ref(false)
const detailLoading = ref(false)
const submitting = ref(false)
const pending = ref([])
const selected = ref(null)
const recommendations = ref([])
const selectedBags = ref([])
const history = ref([])
const keyword = ref('')
const onlyCompatible = ref(false)
const method = ref('微柱凝胶')
const note = ref('')
const tableRef = ref(null)

const methods = ['盐水法', '凝聚胺', '微柱凝胶']

const filteredPending = computed(() => {
  const key = keyword.value.trim().toLowerCase()
  if (!key) return pending.value
  return pending.value.filter((item) =>
    [item.request_no, item.patient_name, item.admission_no, item.department]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(key)),
  )
})

const filteredBags = computed(() =>
  recommendations.value.filter((bag) => !onlyCompatible.value || bag.compatibility?.level !== 'fail'),
)

const selectedTotal = computed(() => selectedBags.value.reduce((sum, bag) => sum + Number(bag.quantity || 0), 0))
const activeBag = computed(() => selectedBags.value[selectedBags.value.length - 1])
const compatibility = computed(() => activeBag.value?.compatibility || { level: 'ok', reason: '勾选血袋后将实时展示相容性判定' })
const enoughQuantity = computed(() => Boolean(selected.value) && selectedTotal.value + 1e-6 >= Number(selected.value.quantity || 0))
const canSubmit = computed(() => Boolean(selected.value && selectedBags.value.length && enoughQuantity.value && !submitting.value))
const activeMatches = computed(() => history.value.filter((item) => item.is_active))

function waitingClass(minutes) {
  if (minutes >= 120) return 'critical'
  if (minutes >= 30) return 'warning'
  return ''
}

function rowClass({ row }) {
  return row.compatibility?.level === 'fail' ? 'incompatible-row' : ''
}

function isSelectable(row) {
  return row.compatibility?.level !== 'fail'
}

function compatTag(level) {
  return { ok: 'success', warn: 'warning', fail: 'danger' }[level] || 'info'
}

async function loadPending() {
  loading.value = true
  try {
    pending.value = await crossMatchApi.pending()
    if (selected.value) {
      selected.value = pending.value.find((item) => item.id === selected.value.id) || null
    }
    if (!selected.value && pending.value.length) {
      await openRequest(pending.value[0])
    }
    if (!pending.value.length) {
      selected.value = null
      recommendations.value = []
      history.value = []
      selectedBags.value = []
    }
  } finally {
    loading.value = false
  }
}

async function openRequest(item) {
  if (!item) return
  selected.value = item
  selectedBags.value = []
  recommendations.value = []
  history.value = []
  note.value = ''
  detailLoading.value = true
  try {
    if (item.status === '待配血') {
      await requestApi.startMatch(item.id)
      item.status = '配血中'
    }
    const [recommendationData, matches] = await Promise.all([
      requestApi.recommendations(item.id),
      crossMatchApi.list({ request_id: item.id }),
    ])
    recommendations.value = recommendationData.bags || []
    history.value = matches || []
  } catch {
    recommendations.value = []
  } finally {
    detailLoading.value = false
  }
}

function handleSelection(rows) {
  selectedBags.value = rows
}

function clearSelection() {
  tableRef.value?.clearSelection()
  selectedBags.value = []
}

async function submitMatch() {
  if (!canSubmit.value) {
    if (!enoughQuantity.value) ElMessage.warning(`所选血袋总量不足申请量 ${selected.value?.quantity}${selected.value?.quantity_unit || ''}`)
    return
  }
  submitting.value = true
  try {
    const result = await crossMatchApi.create({
      request_id: selected.value.id,
      bag_ids: selectedBags.value.map((bag) => bag.id),
      method: method.value,
      major_result: '阴性',
      minor_result: '阴性',
      note: note.value,
    })
    ElMessage.success(result.warnings?.length ? '配血成功，血袋已锁定（含相容性提示）' : '配血成功，血袋已锁定')
    selected.value = null
    await loadPending()
  } finally {
    submitting.value = false
  }
}

async function cancelMatch() {
  if (!selected.value) return
  await ElMessageBox.confirm('取消配血后，已锁定血袋将恢复为在库状态。确认继续？', '取消配血', {
    type: 'warning',
    confirmButtonText: '确认取消配血',
  })
  await crossMatchApi.cancel({ request_id: selected.value.id })
  ElMessage.success('配血已取消，血袋已解锁')
  const id = selected.value.id
  selected.value = null
  await loadPending()
  const next = pending.value.find((item) => item.id === id)
  if (next) await openRequest(next)
}

watch([keyword, onlyCompatible], clearSelection)

onMounted(loadPending)
</script>

<template>
  <div class="page">
    <PageHeader title="配血工作台" description="按 ABO/Rh 规则校验供受者相容性，不相容血袋禁止选择；配血成功后自动锁定血袋">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="loadPending">刷新队列</el-button>
      </template>
    </PageHeader>

    <div class="workbench">
      <aside class="page-card queue-panel" v-loading="loading">
        <div class="panel-title">
          <div>
            <h3>待配血申请</h3>
            <p>{{ pending.length }} 张申请等待处理</p>
          </div>
          <span class="queue-count">{{ pending.length }}</span>
        </div>
        <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="申请单号 / 姓名 / 住院号" size="small" />

        <div class="queue-list">
          <button
            v-for="item in filteredPending"
            :key="item.id"
            type="button"
            class="queue-card focusable"
            :class="{ active: selected?.id === item.id }"
            @click="openRequest(item)"
          >
            <div class="queue-top">
              <span class="request-no">{{ item.request_no }}</span>
              <el-tag :type="item.urgency === '常规' ? 'info' : item.urgency === '紧急' ? 'warning' : 'danger'" size="small" effect="light">{{ item.urgency }}</el-tag>
            </div>
            <div class="patient-line">
              <strong>{{ item.patient_name }}</strong>
              <span>{{ item.department }} · {{ item.bed_no || '未填床号' }}</span>
            </div>
            <div class="queue-meta">
              <BloodBadge :type="item.blood_type" :size="24" />
              <RhTag :rh="item.rh" />
              <span>{{ item.product_name }} {{ item.quantity }}{{ item.quantity_unit }}</span>
            </div>
            <div class="queue-foot">
              <StatusTag :status="item.status" />
              <span class="waiting" :class="waitingClass(item.waiting_minutes)">已等待 {{ item.waiting_minutes }} 分钟</span>
            </div>
          </button>
          <el-empty v-if="!filteredPending.length" :image-size="64" description="暂无待配血申请" />
        </div>
      </aside>

      <section class="page-card match-panel" v-loading="detailLoading">
        <template v-if="selected">
          <div class="match-head">
            <div>
              <span class="eyebrow">{{ selected.request_no }}</span>
              <h2>{{ selected.patient_name }} <small>{{ selected.admission_no }}</small></h2>
              <p>{{ selected.department }} · {{ selected.bed_no || '未填床号' }} · {{ selected.diagnosis }}</p>
            </div>
            <div class="patient-blood">
              <BloodBadge :type="selected.blood_type" :size="40" />
              <RhTag :rh="selected.rh" />
            </div>
          </div>

          <div class="request-facts">
            <div><span>申请品种</span><strong>{{ selected.product_name }}</strong></div>
            <div><span>申请量</span><strong>{{ selected.quantity }}{{ selected.quantity_unit }}</strong></div>
            <div><span>申请医生</span><strong>{{ selected.doctor }}</strong></div>
            <div><span>申请时间</span><strong>{{ formatDateTime(selected.requested_at) }}</strong></div>
          </div>

          <div class="toolbar match-toolbar">
            <el-switch v-model="onlyCompatible" active-text="仅显示相容" />
            <el-select v-model="method" style="width: 132px">
              <el-option v-for="item in methods" :key="item" :label="item" :value="item" />
            </el-select>
          </div>

          <CompatBanner :level="compatibility.level" :reason="compatibility.reason" />

          <el-table
            ref="tableRef"
            :data="filteredBags"
            border
            max-height="360"
            class="bag-table"
            :row-class-name="rowClass"
            @selection-change="handleSelection"
          >
            <el-table-column type="selection" width="46" :selectable="isSelectable" />
            <el-table-column label="储血号" min-width="130">
              <template #default="{ row }"><span class="request-no">{{ row.bag_no }}</span></template>
            </el-table-column>
            <el-table-column label="血型" width="82">
              <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="24" /></template>
            </el-table-column>
            <el-table-column label="Rh" width="82">
              <template #default="{ row }"><RhTag :rh="row.rh" /></template>
            </el-table-column>
            <el-table-column prop="product_name" label="品种" min-width="112" />
            <el-table-column label="数量" width="76" align="right">
              <template #default="{ row }">{{ row.quantity }}{{ selected.quantity_unit }}</template>
            </el-table-column>
            <el-table-column label="有效期" width="112">
              <template #default="{ row }">
                <span :class="row.days_to_expiry <= 3 ? 'text-danger' : row.days_to_expiry <= 7 ? 'text-warning' : ''">{{ formatDate(row.expiry_date) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="相容性" min-width="170">
              <template #default="{ row }">
                <el-tooltip :content="row.compatibility?.reason || '相容'" placement="top">
                  <el-tag :type="compatTag(row.compatibility?.level)" size="small" effect="light">
                    {{ row.compatibility?.level === 'ok' ? '相容' : row.compatibility?.level === 'warn' ? '提示' : '不相容' }}
                  </el-tag>
                </el-tooltip>
                <span v-if="row.compatibility?.level === 'fail'" class="fail-reason">{{ row.compatibility.reason }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div class="submit-bar">
            <div class="selection-summary">
              <span>已选 {{ selectedBags.length }} 袋</span>
              <strong :class="enoughQuantity ? 'text-success' : 'text-danger'">{{ selectedTotal }}{{ selected.quantity_unit }}</strong>
              <span>/ 申请 {{ selected.quantity }}{{ selected.quantity_unit }}</span>
            </div>
            <el-input v-model="note" placeholder="配血备注（可选）" style="width: 260px" />
            <el-button v-if="activeMatches.length" @click="cancelMatch">取消配血</el-button>
            <el-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submitMatch">提交配血并锁定</el-button>
          </div>

          <div v-if="history.length" class="history-block">
            <h3>本次配血记录</h3>
            <el-table :data="history" size="small" border>
              <el-table-column prop="bag_no" label="储血号" min-width="130" />
              <el-table-column prop="method" label="方法" width="100" />
              <el-table-column prop="compatibility" label="判定" width="90">
                <template #default="{ row }"><el-tag :type="row.compatibility === '相容' ? 'success' : 'danger'" size="small">{{ row.compatibility }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="note" label="备注" min-width="220" show-overflow-tooltip />
              <el-table-column label="时间" width="160">
                <template #default="{ row }">{{ formatDateTime(row.matched_at) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="90">
                <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '有效' : '已取消/拦截' }}</el-tag></template>
              </el-table-column>
            </el-table>
          </div>
        </template>
        <el-empty v-else :image-size="110" description="从左侧选择一张待配血申请单开始配血" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 16px;
  min-height: 650px;
}

.queue-panel,
.match-panel {
  min-width: 0;
}

.queue-panel {
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.panel-title,
.match-head,
.queue-top,
.queue-foot,
.submit-bar,
.selection-summary {
  display: flex;
  align-items: center;
}

.panel-title,
.match-head,
.queue-top,
.queue-foot,
.submit-bar {
  justify-content: space-between;
}

.panel-title {
  margin-bottom: 12px;
}

.panel-title h3,
.history-block h3 {
  margin: 0;
  font-size: 14px;
}

.panel-title p {
  margin: 3px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.queue-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: var(--bb-primary);
  font-size: 13px;
  font-weight: 700;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.queue-list {
  flex: 1;
  margin-top: 12px;
  overflow: auto;
}

.queue-card {
  width: 100%;
  padding: 12px;
  margin-bottom: 9px;
  color: var(--bb-text);
  text-align: left;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
  cursor: pointer;
  transition: border-color 150ms, background 150ms, box-shadow 150ms;
}

.queue-card:hover,
.queue-card.active {
  background: var(--bb-hover);
  border-color: #93c5fd;
  box-shadow: inset 3px 0 0 var(--bb-primary);
}

.request-no {
  color: var(--bb-primary);
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.patient-line {
  display: flex;
  gap: 10px;
  align-items: baseline;
  margin: 9px 0 7px;
}

.patient-line strong {
  font-size: 16px;
}

.patient-line span,
.queue-meta span,
.waiting {
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.queue-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 10px;
}

.queue-foot {
  padding-top: 9px;
  border-top: 1px dashed var(--bb-border);
}

.waiting.warning {
  color: var(--bb-warning);
}

.waiting.critical {
  color: var(--bb-danger);
  font-weight: 700;
}

.match-panel {
  padding: 20px;
}

.eyebrow {
  color: var(--bb-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
}

.match-head h2 {
  margin: 6px 0 5px;
  font-size: 23px;
}

.match-head h2 small {
  margin-left: 8px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.match-head p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.patient-blood {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.request-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 14px 0;
  margin: 16px 0 10px;
  border-top: 1px solid var(--bb-border);
  border-bottom: 1px solid var(--bb-border);
}

.request-facts span,
.request-facts strong {
  display: block;
}

.request-facts span {
  margin-bottom: 5px;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.request-facts strong {
  font-size: 12px;
}

.match-toolbar {
  margin: 10px 0;
}

.bag-table {
  margin-top: 12px;
}

.fail-reason {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: var(--bb-danger);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submit-bar {
  gap: 10px;
  padding: 13px 14px;
  margin-top: 14px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.selection-summary {
  gap: 5px;
  margin-right: auto;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.selection-summary strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.history-block {
  margin-top: 22px;
}

.history-block h3 {
  margin-bottom: 10px;
}

:deep(.incompatible-row) {
  background: #fef2f2;
}

:deep(.incompatible-row td:first-child) {
  box-shadow: inset 3px 0 0 var(--bb-danger);
}
</style>
