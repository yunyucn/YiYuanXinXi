<script setup>
/** 输血不良反应列表：筛选、分页、详情查看与全流程追溯入口。 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Search, Warning } from '@element-plus/icons-vue'
import { adverseApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import { formatDateTime, severityType } from '@/utils/format'

const router = useRouter()
const auth = useAuthStore()
/** 护士只看本人上报记录，技师与主任可看全部。 */
const scopedToSelf = computed(() => auth.role === 'nurse')
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

const filters = reactive({ admission_no: '', bag_no: '', reaction_type: '', severity: '' })
const reactionTypes = ['发热', '过敏', '溶血', '其他']
const severities = ['轻度', '中度', '重度']

/** 当前页重度反应数量。 */
const pageSevere = computed(() => items.value.filter((item) => item.severity === '重度').length)
/** 当前页已上报血站数量。 */
const pageReported = computed(() => items.value.filter((item) => item.reported_to_station).length)

/** 按反应程度返回行样式。 */
function rowClass({ row }) {
  return row.severity === '重度' ? 'danger-row' : row.severity === '中度' ? 'warning-row' : ''
}

/** 按当前筛选条件加载不良反应分页数据。 */
async function loadItems() {
  loading.value = true
  try {
    const data = await adverseApi.list({
      admission_no: filters.admission_no || undefined,
      bag_no: filters.bag_no || undefined,
      reaction_type: filters.reaction_type || undefined,
      severity: filters.severity || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

/** 筛选条件变化或回车时回到第一页查询。 */
function search() {
  page.value = 1
  loadItems()
}

/** 清空筛选并重新查询。 */
function resetFilters() {
  Object.assign(filters, { admission_no: '', bag_no: '', reaction_type: '', severity: '' })
  page.value = 1
  loadItems()
}

/** 打开指定不良反应的详情抽屉。 */
async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await adverseApi.detail(row.id)
  } finally {
    detailLoading.value = false
  }
}

/** 跳转到患者全周期追溯页面。 */
function goTrace(admissionNo) {
  router.push({ path: '/trace', query: { admission_no: admissionNo } })
}

/** 组装表格操作列配置。 */
function adverseActions(row) {
  return [
    { label: '详情', onClick: () => openDetail(row) },
    { label: '追溯', type: 'info', onClick: () => goTrace(row.admission_no) },
  ]
}

onMounted(loadItems)
</script>

<template>
  <div class="page">
    <PageHeader title="输血不良反应" :description="scopedToSelf ? '仅显示本人上报的不良反应记录，支持按住院号、储血号、类型和程度筛选' : '汇总护士上报的发热、过敏、溶血等输血反应，支持按住院号、储血号、类型和程度筛选'">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="loadItems">刷新</el-button>
      </template>
    </PageHeader>

    <div class="summary-strip">
      <div class="page-card summary-item"><span>记录总数</span><strong>{{ total }}</strong><small>条不良反应</small></div>
      <div class="page-card summary-item warning"><span>本页中度</span><strong>{{ items.filter((item) => item.severity === '中度').length }}</strong><small>需持续观察</small></div>
      <div class="page-card summary-item danger"><span>本页重度</span><strong>{{ pageSevere }}</strong><small>重点复盘病例</small></div>
      <div class="page-card summary-item success"><span>本页已上报血站</span><strong>{{ pageReported }}</strong><small>完成外部上报</small></div>
    </div>

    <section class="page-card">
      <div class="filter-bar">
        <el-input v-model="filters.admission_no" clearable placeholder="住院号" style="width: 150px" @keyup.enter="search" />
        <el-input v-model="filters.bag_no" clearable placeholder="储血号" style="width: 160px" @keyup.enter="search" />
        <el-select v-model="filters.reaction_type" clearable placeholder="反应类型" style="width: 130px" @change="search">
          <el-option v-for="item in reactionTypes" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.severity" clearable placeholder="反应程度" style="width: 130px" @change="search">
          <el-option v-for="item in severities" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
        <span class="nurse-tip">护士可在“输血执行 → 已完成记录”中新增不良反应。</span>
      </div>

      <el-table v-loading="loading" :data="items" border :row-class-name="rowClass">
        <el-table-column label="发生时间" width="158">
          <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column prop="patient_name" label="患者" width="96" />
        <el-table-column prop="admission_no" label="住院号" width="130">
          <template #default="{ row }"><el-button text type="primary" @click="goTrace(row.admission_no)">{{ row.admission_no }}</el-button></template>
        </el-table-column>
        <el-table-column prop="bag_no" label="储血号" width="140" />
        <el-table-column label="反应类型" width="100">
          <template #default="{ row }"><el-tag type="warning" size="small" effect="light">{{ row.reaction_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="程度" width="88">
          <template #default="{ row }"><el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="treatment" label="处理措施" min-width="250" show-overflow-tooltip />
        <el-table-column label="上报血站" width="92" align="center">
          <template #default="{ row }"><el-tag :type="row.reported_to_station ? 'success' : 'info'" size="small">{{ row.reported_to_station ? '已上报' : '未上报' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="nurse" label="记录护士" width="100" />
        <el-table-column label="操作" width="108" fixed="right" align="center">
          <template #default="{ row }"><TableActions :actions="adverseActions(row)" /></template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadItems" @size-change="loadItems" />
      </div>
    </section>

    <el-drawer v-model="detailVisible" title="不良反应详情" size="600px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="detail-head">
            <div class="warning-icon"><el-icon><Warning /></el-icon></div>
            <div>
              <span class="eyebrow">{{ detail.record_no }}</span>
              <h2>{{ detail.patient_name }} <small>{{ detail.admission_no }}</small></h2>
              <p>{{ detail.bag_no }} · {{ formatDateTime(detail.occurred_at) }}</p>
            </div>
            <el-tag :type="severityType(detail.severity)" size="large">{{ detail.severity }}</el-tag>
          </div>

          <div class="detail-grid">
            <div class="detail-item"><span class="label">反应类型</span><span class="value">{{ detail.reaction_type }}</span></div>
            <div class="detail-item"><span class="label">记录护士</span><span class="value">{{ detail.nurse }}</span></div>
            <div class="detail-item"><span class="label">发生时间</span><span class="value">{{ formatDateTime(detail.occurred_at) }}</span></div>
            <div class="detail-item"><span class="label">上报血站</span><span class="value">{{ detail.reported_to_station ? '已上报' : '未上报' }}</span></div>
          </div>

          <h3 class="section-title">处理措施</h3>
          <p class="treatment-text">{{ detail.treatment }}</p>

          <h3 class="section-title">补充说明</h3>
          <p class="treatment-text">{{ detail.note || '无补充说明' }}</p>

          <div class="drawer-actions">
            <el-button @click="detailVisible = false">关闭</el-button>
            <el-button type="primary" @click="goTrace(detail.admission_no)">查看全周期追溯</el-button>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.summary-item.danger {
  border-left-color: var(--bb-danger);
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
  font-size: 25px;
  line-height: 1;
}

.nurse-tip {
  margin-left: auto;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.detail-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--bb-border);
}

.warning-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  color: var(--bb-warning);
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 4px;
}

.detail-head > div:nth-child(2) {
  flex: 1;
}

.eyebrow {
  color: var(--bb-primary);
  font-size: 10px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.detail-head h2 {
  margin: 5px 0 4px;
  font-size: 21px;
}

.detail-head h2 small {
  margin-left: 7px;
  color: var(--bb-text-secondary);
  font-size: 11px;
  font-weight: 400;
}

.detail-head p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.treatment-text {
  padding: 12px 14px;
  margin: 0;
  color: var(--bb-text);
  font-size: 12px;
  line-height: 1.7;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 18px;
  margin-top: 20px;
  border-top: 1px solid var(--bb-border);
}

:deep(.danger-row td:first-child) {
  box-shadow: inset 3px 0 0 var(--bb-danger);
}

:deep(.warning-row td:first-child) {
  box-shadow: inset 3px 0 0 var(--bb-warning);
}
</style>
