<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Printer, Refresh, Search } from '@element-plus/icons-vue'
import { issueApi } from '@/api'
import { formatDate, formatDateTime } from '@/utils/format'

const activeTab = ref('pending')
const loading = ref(false)
const issuing = ref(false)
const pending = ref([])
const selected = ref(null)
const checks = ref([])
const pickupNurse = ref('')
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

const filters = reactive({ keyword: '', execution_status: '' })

const checkOptions = [
  '申请单与血袋信息一致',
  '血袋外观无破损、无渗漏',
  '血袋在有效期内',
  '配血结果相容',
]

const allChecked = computed(() => checkOptions.every((item) => checks.value.includes(item)))
const selectedQuantity = computed(() => (selected.value?.bags || []).reduce((sum, bag) => sum + Number(bag.quantity || 0), 0))
const pendingCount = computed(() => pending.value.length)

async function loadPending() {
  loading.value = true
  try {
    pending.value = await issueApi.pending()
    if (selected.value) selected.value = pending.value.find((item) => item.id === selected.value.id) || null
    if (!selected.value && pending.value.length) selectPending(pending.value[0])
  } finally {
    loading.value = false
  }
}

async function loadRecords() {
  const data = await issueApi.list({
    keyword: filters.keyword || undefined,
    execution_status: filters.execution_status || undefined,
    page: page.value,
    page_size: pageSize.value,
  })
  records.value = data.items
  total.value = data.total
}

async function refreshAll() {
  await Promise.all([loadPending(), loadRecords()])
}

function selectPending(item) {
  selected.value = item
  checks.value = []
  pickupNurse.value = ''
}

function resetForm() {
  checks.value = []
  pickupNurse.value = ''
}

async function submitIssue() {
  if (!selected.value) return
  if (!pickupNurse.value.trim()) {
    ElMessage.warning('请填写领血护士姓名')
    return
  }
  if (!allChecked.value) {
    ElMessage.warning('发血前四项核对必须全部完成')
    return
  }
  issuing.value = true
  try {
    const result = await issueApi.create({
      request_id: selected.value.id,
      pickup_nurse: pickupNurse.value.trim(),
      check_items: checks.value,
    })
    ElMessage.success('发血成功，血袋状态已联动更新')
    selected.value = null
    resetForm()
    await refreshAll()
    try {
      await ElMessageBox.confirm('发血记录已生成，是否立即打印输血记录单？', '打印记录单', {
        confirmButtonText: '立即打印',
        cancelButtonText: '稍后打印',
        type: 'success',
      })
      window.open(`/print/record/${result.id}`, '_blank')
    } catch {
      // 用户选择稍后打印
    }
  } finally {
    issuing.value = false
  }
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await issueApi.detail(row.id)
  } finally {
    detailLoading.value = false
  }
}

function printRecord(id) {
  window.open(`/print/record/${id}`, '_blank')
}

function printLabel(bagId) {
  window.open(`/print/label/${bagId}`, '_blank')
}

function searchRecords() {
  page.value = 1
  loadRecords()
}

function resetRecords() {
  filters.keyword = ''
  filters.execution_status = ''
  page.value = 1
  loadRecords()
}

function issueActions(row) {
  return [
    { label: '详情', onClick: () => openDetail(row) },
    { label: '记录单', icon: Printer, onClick: () => printRecord(row.id) },
  ]
}

onMounted(refreshAll)
</script>

<template>
  <div class="page">
    <PageHeader title="发血工作台" description="完成申请单、血袋、效期与配血结果四项核对后发血，并联动血袋、申请单和库存状态">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="refreshAll">刷新</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab" class="page-card issue-tabs">
      <el-tab-pane :label="`待发血（${pendingCount}）`" name="pending">
        <div class="workbench">
          <aside class="queue-panel" v-loading="loading">
            <div class="panel-title">
              <div>
                <h3>已备血申请</h3>
                <p>配血完成且血袋已锁定</p>
              </div>
            </div>
            <div class="queue-list">
              <button
                v-for="item in pending"
                :key="item.id"
                type="button"
                class="queue-card focusable"
                :class="{ active: selected?.id === item.id }"
                @click="selectPending(item)"
              >
                <div class="queue-top">
                  <span class="request-no">{{ item.request_no }}</span>
                  <StatusTag :status="item.status" />
                </div>
                <div class="patient-line">
                  <strong>{{ item.patient_name }}</strong>
                  <span>{{ item.admission_no }}</span>
                </div>
                <div class="queue-meta">
                  <BloodBadge :type="item.blood_type" :size="24" />
                  <RhTag :rh="item.rh" />
                  <span>{{ item.department }} · {{ item.bed_no || '未填床号' }}</span>
                </div>
                <div class="queue-foot">
                  <span>{{ item.product_name }} {{ item.quantity }}{{ item.quantity_unit }}</span>
                  <span>{{ item.bags?.length || 0 }} 袋已锁定</span>
                </div>
              </button>
              <el-empty v-if="!pending.length" :image-size="72" description="暂无待发血申请" />
            </div>
          </aside>

          <section class="issue-panel">
            <template v-if="selected">
              <div class="issue-head">
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
                <div><span>品种</span><strong>{{ selected.product_name }}</strong></div>
                <div><span>申请量</span><strong>{{ selected.quantity }}{{ selected.quantity_unit }}</strong></div>
                <div><span>已配血袋</span><strong>{{ selected.bags?.length || 0 }} 袋 / {{ selectedQuantity }}{{ selected.quantity_unit }}</strong></div>
                <div><span>申请医生</span><strong>{{ selected.doctor }}</strong></div>
              </div>

              <h3 class="section-title">待发放血袋</h3>
              <el-table :data="selected.bags || []" border>
                <el-table-column prop="bag_no" label="储血号" min-width="140">
                  <template #default="{ row }"><span class="request-no">{{ row.bag_no }}</span></template>
                </el-table-column>
                <el-table-column label="血型" width="90">
                  <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="24" /></template>
                </el-table-column>
                <el-table-column label="Rh" width="88">
                  <template #default="{ row }"><RhTag :rh="row.rh" /></template>
                </el-table-column>
                <el-table-column prop="product_name" label="品种" min-width="120" />
                <el-table-column prop="specification" label="规格" width="92" />
                <el-table-column label="数量" width="82" align="right">
                  <template #default="{ row }">{{ row.quantity }}{{ selected.quantity_unit }}</template>
                </el-table-column>
                <el-table-column label="有效期" width="116">
                  <template #default="{ row }">{{ formatDate(row.expiry_date) }}</template>
                </el-table-column>
                <el-table-column label="储存位置" width="118">
                  <template #default="{ row }">{{ row.fridge_code || row.storage_location || '-' }}</template>
                </el-table-column>
              </el-table>

              <div class="check-block">
                <div class="check-head">
                  <div>
                    <h3>发血前核对</h3>
                    <p>四项核对必须全部完成，系统才允许发血</p>
                  </div>
                  <span :class="allChecked ? 'text-success' : 'text-warning'">{{ checks.length }}/4 已完成</span>
                </div>
                <el-checkbox-group v-model="checks" class="check-grid">
                  <el-checkbox v-for="item in checkOptions" :key="item" :value="item">{{ item }}</el-checkbox>
                </el-checkbox-group>
                <div class="issue-actions">
                  <div class="nurse-field">
                    <span>领血护士</span>
                    <el-input v-model="pickupNurse" placeholder="请输入领血护士姓名" style="width: 220px" />
                  </div>
                  <el-button @click="resetForm">清空核对</el-button>
                  <el-button type="primary" :loading="issuing" :disabled="!allChecked || !pickupNurse.trim()" @click="submitIssue">确认发血</el-button>
                </div>
              </div>
            </template>
            <el-empty v-else :image-size="110" description="从左侧选择一张已备血申请单" />
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="发血记录" name="records">
        <div class="filter-bar">
          <el-input v-model="filters.keyword" :prefix-icon="Search" clearable placeholder="记录号 / 申请单号 / 患者" style="width: 280px" @keyup.enter="searchRecords" />
          <el-select v-model="filters.execution_status" clearable placeholder="执行状态" style="width: 140px">
            <el-option label="待执行" value="待执行" />
            <el-option label="已完成" value="已完成" />
          </el-select>
          <el-button type="primary" :icon="Search" @click="searchRecords">查询</el-button>
          <el-button @click="resetRecords">重置</el-button>
        </div>
        <el-table :data="records" border>
          <el-table-column prop="record_no" label="发血记录号" min-width="190">
            <template #default="{ row }"><span class="request-no">{{ row.record_no }}</span></template>
          </el-table-column>
          <el-table-column prop="patient_name" label="患者" width="100" />
          <el-table-column prop="admission_no" label="住院号" width="130" />
          <el-table-column prop="department" label="科室" width="110" />
          <el-table-column prop="product_name" label="品种" min-width="110" />
          <el-table-column label="血袋" width="74" align="center">
            <template #default="{ row }">{{ row.bags?.length || 0 }} 袋</template>
          </el-table-column>
          <el-table-column prop="pickup_nurse" label="领血护士" width="100" />
          <el-table-column label="发血时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.issued_at) }}</template>
          </el-table-column>
          <el-table-column label="执行状态" width="96">
            <template #default="{ row }"><StatusTag :status="row.execution_status" /></template>
          </el-table-column>
          <el-table-column label="操作" width="152" fixed="right" align="center">
            <template #default="{ row }"><TableActions :actions="issueActions(row)" /></template>
          </el-table-column>
        </el-table>
        <div class="table-footer">
          <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadRecords" @size-change="loadRecords" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="detailVisible" title="发血记录详情" size="760px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="detail-hero">
            <div>
              <span class="eyebrow">{{ detail.record_no }}</span>
              <h2>{{ detail.patient_name }} <small>{{ detail.admission_no }}</small></h2>
              <p>{{ detail.department }} · {{ detail.bed_no || '未填床号' }} · {{ detail.product_name }}</p>
            </div>
            <StatusTag :status="detail.execution_status" />
          </div>

          <div class="detail-grid">
            <div class="detail-item"><span class="label">申请单号</span><span class="value">{{ detail.request_no }}</span></div>
            <div class="detail-item"><span class="label">发血人</span><span class="value">{{ detail.issued_by }}</span></div>
            <div class="detail-item"><span class="label">领血护士</span><span class="value">{{ detail.pickup_nurse }}</span></div>
            <div class="detail-item"><span class="label">发血时间</span><span class="value">{{ formatDateTime(detail.issued_at) }}</span></div>
            <div class="detail-item"><span class="label">执行人</span><span class="value">{{ detail.executed_by || '-' }}</span></div>
            <div class="detail-item"><span class="label">执行时间</span><span class="value">{{ formatDateTime(detail.executed_at) }}</span></div>
          </div>

          <h3 class="section-title">血袋明细</h3>
          <el-table :data="detail.bags" border size="small">
            <el-table-column prop="bag_no" label="储血号" min-width="130" />
            <el-table-column label="血型" width="84">
              <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="22" /></template>
            </el-table-column>
            <el-table-column label="Rh" width="82">
              <template #default="{ row }"><RhTag :rh="row.rh" /></template>
            </el-table-column>
            <el-table-column prop="product_name" label="品种" min-width="110" />
            <el-table-column prop="quantity" label="数量" width="72" align="right" />
            <el-table-column label="有效期" width="108">
              <template #default="{ row }">{{ formatDate(row.expiry_date) }}</template>
            </el-table-column>
            <el-table-column label="袋签" width="76">
              <template #default="{ row }"><el-button text type="primary" :icon="Printer" @click="printLabel(row.id)">打印</el-button></template>
            </el-table-column>
          </el-table>

          <h3 class="section-title">核对项</h3>
          <div class="check-tags">
            <el-tag v-for="item in detail.check_items" :key="item" type="success" effect="light">{{ item }}</el-tag>
          </div>

          <template v-if="detail.adverse_reactions?.length">
            <h3 class="section-title">不良反应</h3>
            <div v-for="item in detail.adverse_reactions" :key="item.id" class="adverse-line">
              <el-tag type="warning">{{ item.reaction_type }}</el-tag>
              <el-tag type="danger" effect="plain">{{ item.severity }}</el-tag>
              <span>{{ formatDateTime(item.occurred_at) }}</span>
              <p>{{ item.treatment }}</p>
            </div>
          </template>

          <div class="drawer-actions">
            <el-button @click="detailVisible = false">关闭</el-button>
            <el-button type="primary" :icon="Printer" @click="printRecord(detail.id)">打印输血记录单</el-button>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.issue-tabs {
  min-height: 690px;
}

.workbench {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  gap: 18px;
  min-height: 620px;
}

.queue-panel {
  min-width: 0;
  padding-right: 18px;
  border-right: 1px solid var(--bb-border);
}

.panel-title,
.queue-top,
.queue-foot,
.issue-head,
.check-head,
.issue-actions,
.detail-hero,
.adverse-line {
  display: flex;
  align-items: center;
}

.queue-top,
.queue-foot,
.issue-head,
.check-head,
.issue-actions,
.detail-hero {
  justify-content: space-between;
}

.panel-title h3,
.check-head h3 {
  margin: 0;
  font-size: 14px;
}

.panel-title p,
.check-head p {
  margin: 3px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.queue-list {
  margin-top: 12px;
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
}

.queue-card:hover,
.queue-card.active {
  background: var(--bb-hover);
  border-color: #93c5fd;
  box-shadow: inset 3px 0 0 var(--bb-primary);
}

.request-no,
.eyebrow {
  color: var(--bb-primary);
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.patient-line {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin: 9px 0 7px;
}

.patient-line strong {
  font-size: 16px;
}

.patient-line span,
.queue-meta span,
.queue-foot {
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.queue-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 9px;
}

.queue-foot {
  padding-top: 8px;
  border-top: 1px dashed var(--bb-border);
}

.issue-panel {
  min-width: 0;
}

.issue-head h2,
.detail-hero h2 {
  margin: 6px 0 5px;
  font-size: 23px;
}

.issue-head h2 small,
.detail-hero h2 small {
  margin-left: 8px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.issue-head p,
.detail-hero p {
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
  margin: 16px 0;
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

.check-block {
  padding: 16px;
  margin-top: 18px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.check-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 20px;
  padding: 14px 0;
}

.issue-actions {
  gap: 10px;
  padding-top: 14px;
  border-top: 1px dashed var(--bb-border);
}

.nurse-field {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-right: auto;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.detail-hero {
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--bb-border);
}

.check-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.adverse-line {
  gap: 8px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--bb-border);
}

.adverse-line span {
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.adverse-line p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid var(--bb-border);
}
</style>
