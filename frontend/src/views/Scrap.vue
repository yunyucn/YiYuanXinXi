<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Delete, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { bagApi, scrapApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import { formatDate, formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ approval_status: '', keyword: '' })
const createVisible = ref(false)
const createLoading = ref(false)
const bags = ref([])
const bagLoading = ref(false)
const selectedBags = ref([])
const scrapReason = ref('')
const batchLoading = ref(false)

const canApply = computed(() => auth.canAccess('scrapApply'))
const canApprove = computed(() => auth.canAccess('scrapApprove'))
const pendingOnPage = computed(() => items.value.filter((item) => item.approval_status === '待审批').length)
const approvedOnPage = computed(() => items.value.filter((item) => item.approval_status === '已批准').length)

function statusTag(status) {
  return { 待审批: 'warning', 已批准: 'success', 已驳回: 'danger' }[status] || 'info'
}

function isSelectable(row) {
  return !['备血锁定', '已发血', '已报废'].includes(row.status)
}

async function loadItems() {
  loading.value = true
  try {
    const data = await scrapApi.list({
      approval_status: filters.approval_status || undefined,
      keyword: filters.keyword || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadBags() {
  bagLoading.value = true
  try {
    const data = await bagApi.list({ page: 1, page_size: 100 })
    bags.value = data.items
  } finally {
    bagLoading.value = false
  }
}

function search() {
  page.value = 1
  loadItems()
}

function resetFilters() {
  filters.approval_status = ''
  filters.keyword = ''
  page.value = 1
  loadItems()
}

async function openCreate() {
  createVisible.value = true
  selectedBags.value = []
  scrapReason.value = ''
  await loadBags()
}

async function submitCreate() {
  if (!selectedBags.value.length) {
    ElMessage.warning('请选择需要报废的血袋')
    return
  }
  if (!scrapReason.value.trim()) {
    ElMessage.warning('请填写报废原因')
    return
  }
  createLoading.value = true
  try {
    await scrapApi.create({ bag_ids: selectedBags.value.map((bag) => bag.id), reason: scrapReason.value.trim() })
    ElMessage.success(`已提交 ${selectedBags.value.length} 条报废申请`)
    createVisible.value = false
    await loadItems()
  } finally {
    createLoading.value = false
  }
}

async function batchExpired() {
  await ElMessageBox.confirm('系统将为所有“已过期”且无待审批记录的血袋批量提交报废申请。确认继续？', '批量过期报废', {
    type: 'warning',
    confirmButtonText: '开始批量申请',
  })
  batchLoading.value = true
  try {
    const result = await scrapApi.expiredBatch()
    ElMessage.success(`已为 ${result.created} 袋过期血液提交报废申请`)
    await loadItems()
  } finally {
    batchLoading.value = false
  }
}

async function review(row, approved) {
  const action = approved ? '批准' : '驳回'
  let note = ''
  try {
    const result = await ElMessageBox.prompt(
      `血袋 ${row.bag_no} 报废原因：${row.reason}\n请输入${action}备注（可选）`,
      `${action}报废申请`,
      {
        confirmButtonText: `确认${action}`,
        cancelButtonText: '取消',
        inputPlaceholder: '审批备注（可选）',
        inputType: 'textarea',
        type: approved ? 'warning' : 'info',
      },
    )
    note = result.value || ''
  } catch {
    return
  }
  if (approved) await scrapApi.approve(row.id, { note })
  else await scrapApi.reject(row.id, { note })
  ElMessage.success(`报废申请已${action}`)
  await loadItems()
}

function scrapActions(row) {
  return [
    { label: '批准', type: 'success', icon: Check, emphasis: true, onClick: () => review(row, true) },
    { label: '驳回', type: 'danger', onClick: () => review(row, false) },
  ]
}

onMounted(loadItems)
</script>

<template>
  <div class="page">
    <PageHeader title="报废管理" description="技师提交报废申请，科室主任审批；批准后血袋状态变更为已报废，过期血液可批量申请">
      <template #actions>
        <el-button v-if="canApply" :icon="Delete" :loading="batchLoading" @click="batchExpired">批量过期报废</el-button>
        <el-button v-if="canApply" type="primary" :icon="Plus" @click="openCreate">新建报废申请</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadItems">刷新</el-button>
      </template>
    </PageHeader>

    <div class="workflow-strip">
      <div><span class="step">01</span><strong>提交申请</strong><small>输血科技师选择血袋并填写原因</small></div>
      <i />
      <div><span class="step">02</span><strong>主任审批</strong><small>科室主任核对原因并批准或驳回</small></div>
      <i />
      <div><span class="step">03</span><strong>状态联动</strong><small>批准后血袋转为已报废并写入操作日志</small></div>
    </div>

    <div class="summary-strip">
      <div class="page-card summary-item"><span>报废记录</span><strong>{{ total }}</strong><small>条记录</small></div>
      <div class="page-card summary-item warning"><span>本页待审批</span><strong>{{ pendingOnPage }}</strong><small>等待主任处理</small></div>
      <div class="page-card summary-item success"><span>本页已批准</span><strong>{{ approvedOnPage }}</strong><small>已完成报废</small></div>
    </div>

    <section class="page-card">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" :prefix-icon="Search" clearable placeholder="储血号 / 报废原因" style="width: 250px" @keyup.enter="search" />
        <el-select v-model="filters.approval_status" clearable placeholder="审批状态" style="width: 140px" @change="search">
          <el-option label="待审批" value="待审批" />
          <el-option label="已批准" value="已批准" />
          <el-option label="已驳回" value="已驳回" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="items" border>
        <el-table-column prop="bag_no" label="储血号" min-width="140">
          <template #default="{ row }"><span class="bag-no">{{ row.bag_no }}</span></template>
        </el-table-column>
        <el-table-column prop="product_name" label="品种" min-width="112" />
        <el-table-column label="血型" width="84">
          <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="24" /></template>
        </el-table-column>
        <el-table-column label="Rh" width="82">
          <template #default="{ row }"><RhTag :rh="row.rh" /></template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="76" align="right" />
        <el-table-column prop="reason" label="报废原因" min-width="220" show-overflow-tooltip />
        <el-table-column prop="handler" label="经手人" width="94" />
        <el-table-column label="申请时间" width="158">
          <template #default="{ row }">{{ formatDateTime(row.applied_at) }}</template>
        </el-table-column>
        <el-table-column label="审批状态" width="96">
          <template #default="{ row }"><el-tag :type="statusTag(row.approval_status)" size="small">{{ row.approval_status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="approver" label="审批人" width="94">
          <template #default="{ row }">{{ row.approver || '-' }}</template>
        </el-table-column>
        <el-table-column label="报废日期" width="108">
          <template #default="{ row }">{{ formatDate(row.scrap_date) }}</template>
        </el-table-column>
        <el-table-column v-if="canApprove" label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions v-if="row.approval_status === '待审批'" :actions="scrapActions(row)" />
            <span v-else class="muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadItems" @size-change="loadItems" />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="新建报废申请" width="780px" destroy-on-close>
      <div class="dialog-tip">仅可选择在库或已过期血袋；备血锁定、已发血、已报废血袋不可申请。</div>
      <el-table v-loading="bagLoading" :data="bags" border max-height="360" @selection-change="selectedBags = $event">
        <el-table-column type="selection" width="46" :selectable="isSelectable" />
        <el-table-column prop="bag_no" label="储血号" min-width="140" />
        <el-table-column prop="product_name" label="品种" min-width="110" />
        <el-table-column label="血型" width="84">
          <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="22" /></template>
        </el-table-column>
        <el-table-column label="Rh" width="78">
          <template #default="{ row }"><RhTag :rh="row.rh" /></template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="72" align="right" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="有效期" width="108">
          <template #default="{ row }"><span :class="row.days_to_expiry <= 0 ? 'text-danger' : ''">{{ formatDate(row.expiry_date) }}</span></template>
        </el-table-column>
      </el-table>
      <el-form label-position="top" class="reason-form">
        <el-form-item label="报废原因">
          <el-input v-model="scrapReason" type="textarea" :rows="3" placeholder="如：血袋外观破损、复检结果异常、过期报废等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="selected-count">已选 {{ selectedBags.length }} 袋</span>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreate">提交报废申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workflow-strip {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 36px minmax(0, 1fr) 36px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 14px 18px;
  margin-bottom: 16px;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 6px;
}

.workflow-strip > div {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 2px 9px;
  align-items: center;
}

.workflow-strip .step {
  display: flex;
  grid-row: 1 / 3;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--bb-primary);
  font-size: 11px;
  font-weight: 700;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.workflow-strip strong {
  font-size: 12px;
}

.workflow-strip small {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.workflow-strip > i {
  height: 1px;
  background: var(--bb-border);
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.summary-item {
  padding: 14px 16px;
  border-left: 3px solid var(--bb-primary);
}

.summary-item.warning {
  border-left-color: var(--bb-warning);
}

.summary-item.success {
  border-left-color: var(--bb-success);
}

.summary-item span,
.summary-item small {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.summary-item strong {
  display: inline-block;
  margin: 5px 5px 3px 0;
  font-size: 24px;
  line-height: 1;
}

.bag-no {
  color: var(--bb-primary);
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.dialog-tip {
  padding: 9px 11px;
  margin-bottom: 12px;
  color: #92400e;
  font-size: 11px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 4px;
}

.reason-form {
  margin-top: 16px;
}

.selected-count {
  float: left;
  color: var(--bb-text-secondary);
  font-size: 12px;
  line-height: 32px;
}
</style>
