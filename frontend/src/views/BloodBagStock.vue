<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Printer, Refresh, Search } from '@element-plus/icons-vue'
import { bagApi, scrapApi, systemApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import { formatDate, formatDateTime } from '@/utils/format'

const route = useRoute()
const auth = useAuthStore()
const activeTab = ref('list')
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const selection = ref([])
const products = ref([])
const fridges = ref([])
const fridgeData = ref([])
const selectedFridgeId = ref(null)
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const scrapVisible = ref(false)
const scrapLoading = ref(false)
const scrapForm = reactive({ bag_ids: [], reason: '' })

const filters = reactive({
  status: '',
  product_name: '',
  blood_type: '',
  fridge_id: null,
  keyword: '',
})

const statuses = ['在库', '备血锁定', '已发血', '已报废', '已过期']
const bloodTypes = ['A', 'B', 'AB', 'O']
const canOperate = computed(() => auth.canAccess('stockOperate'))
const selectedFridge = computed(() => fridgeData.value.find((item) => item.id === selectedFridgeId.value))

function rowClass({ row }) {
  if (row.status === '已过期' || row.expiry_level === 'expired') return 'expired-row'
  if (row.expiry_level === 'danger') return 'danger-row'
  if (row.expiry_level === 'warning') return 'warning-row'
  return ''
}

async function loadBags() {
  loading.value = true
  try {
    const data = await bagApi.list({
      ...filters,
      fridge_id: filters.fridge_id || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadFridges() {
  fridgeData.value = await bagApi.fridgeOverview()
  if (!selectedFridgeId.value && fridgeData.value.length) {
    selectedFridgeId.value = fridgeData.value[0].id
  }
}

function search() {
  page.value = 1
  loadBags()
}

function resetFilters() {
  Object.assign(filters, { status: '', product_name: '', blood_type: '', fridge_id: null, keyword: '' })
  page.value = 1
  loadBags()
}

async function openDetail(rowOrId) {
  const id = typeof rowOrId === 'object' ? rowOrId.id : rowOrId
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await bagApi.detail(id)
  } finally {
    detailLoading.value = false
  }
}

function printLabel(row) {
  window.open(`/print/label/${row.id}`, '_blank')
}

function openScrap(rows) {
  scrapForm.bag_ids = rows.map((row) => row.id)
  scrapForm.reason = ''
  scrapVisible.value = true
}

function bagActions(row) {
  const actions = [
    { label: '详情', onClick: () => openDetail(row) },
    { label: '袋签', type: 'info', icon: Printer, onClick: () => printLabel(row) },
  ]
  if (canOperate.value && ['在库', '已过期'].includes(row.status)) {
    actions.push({ label: '报废', type: 'danger', icon: Delete, onClick: () => openScrap([row]) })
  }
  return actions
}

async function submitScrap() {
  if (!scrapForm.bag_ids.length) {
    ElMessage.warning('请选择报废血袋')
    return
  }
  if (!scrapForm.reason.trim()) {
    ElMessage.warning('请填写报废原因')
    return
  }
  scrapLoading.value = true
  try {
    await scrapApi.create({ bag_ids: scrapForm.bag_ids, reason: scrapForm.reason })
    ElMessage.success('报废申请已提交，等待科室主任审批')
    scrapVisible.value = false
    selection.value = []
    await Promise.all([loadBags(), loadFridges()])
  } finally {
    scrapLoading.value = false
  }
}

function batchScrap() {
  if (!selection.value.length) {
    ElMessage.warning('请先勾选需要报废的血袋')
    return
  }
  openScrap(selection.value)
}

function cellClass(bag) {
  return `cell-${bag.expiry_level || 'ok'}`
}

function cellTitle(bag) {
  return `${bag.bag_no}｜${bag.product_name}｜${bag.blood_type} ${bag.rh}｜有效期 ${formatDate(bag.expiry_date)}｜${bag.days_to_expiry <= 0 ? '已过期' : bag.days_to_expiry + ' 天'}`
}

watch(activeTab, (value) => {
  if (value === 'fridge') loadFridges()
})

onMounted(async () => {
  const [productList, fridgeList] = await Promise.all([systemApi.products(), systemApi.fridges()])
  products.value = productList
  fridges.value = fridgeList
  await Promise.all([loadBags(), loadFridges()])
  if (route.query.bag_id) openDetail(Number(route.query.bag_id))
})
</script>

<template>
  <div class="page">
    <PageHeader title="库存管理" description="按效期倒计时监控库存；冰箱视图展示实物分布，已发血与已报废血袋不再出现">
      <template #actions>
        <el-button v-if="canOperate" :icon="Delete" :disabled="!selection.length" @click="batchScrap">批量报废</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="activeTab === 'list' ? loadBags() : loadFridges()">刷新</el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab" class="page-card stock-tabs">
      <el-tab-pane label="列表视图" name="list">
        <div class="filter-bar">
          <el-input v-model="filters.keyword" placeholder="储血号 / 献血者编号" clearable style="width: 210px" @keyup.enter="search">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="filters.product_name" placeholder="血液品种" clearable style="width: 140px" @change="search">
            <el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.name" />
          </el-select>
          <el-select v-model="filters.blood_type" placeholder="ABO 血型" clearable style="width: 110px" @change="search">
            <el-option v-for="type in bloodTypes" :key="type" :label="type" :value="type" />
          </el-select>
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="search">
            <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
          </el-select>
          <el-select v-model="filters.fridge_id" placeholder="冰箱" clearable style="width: 140px" @change="search">
            <el-option v-for="fridge in fridges" :key="fridge.id" :label="fridge.code" :value="fridge.id" />
          </el-select>
          <el-button type="primary" @click="search">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>

        <el-table
          v-loading="loading"
          :data="items"
          border
          height="520"
          :row-class-name="rowClass"
          @selection-change="(rows) => (selection = rows)"
        >
          <el-table-column v-if="canOperate" type="selection" width="42" />
          <el-table-column prop="bag_no" label="储血号" min-width="150" fixed>
            <template #default="{ row }"><span class="bag-no clickable" @click="openDetail(row)">{{ row.bag_no }}</span></template>
          </el-table-column>
          <el-table-column label="血型" width="78">
            <template #default="{ row }">
              <div class="blood-cell"><BloodBadge :type="row.blood_type" :size="24" /><RhTag :rh="row.rh" /></div>
            </template>
          </el-table-column>
          <el-table-column prop="product_name" label="品种" width="110" />
          <el-table-column prop="specification" label="规格" width="80" />
          <el-table-column label="数量" width="75" align="right">
            <template #default="{ row }"><span class="tabular">{{ row.quantity }}</span></template>
          </el-table-column>
          <el-table-column label="冰箱" width="80">
            <template #default="{ row }">{{ row.fridge_code || '-' }}</template>
          </el-table-column>
          <el-table-column label="有效期" width="210">
            <template #default="{ row }">
              <ExpiryBar :expiry-date="row.expiry_date" :days="row.days_to_expiry" :level="row.expiry_level" :status="row.status" />
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }"><StatusTag :status="row.status" /></template>
          </el-table-column>
          <el-table-column prop="donor_no" label="献血者" min-width="115" />
          <el-table-column label="操作" width="184" fixed="right" align="center">
            <template #default="{ row }"><TableActions :actions="bagActions(row)" /></template>
          </el-table-column>
        </el-table>
        <div class="table-footer">
          <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadBags" @size-change="search" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="冰箱视图" name="fridge">
        <div v-loading="loading" class="fridge-cards">
          <button
            v-for="fridge in fridgeData"
            :key="fridge.id"
            type="button"
            class="fridge-card"
            :class="{ active: selectedFridgeId === fridge.id }"
            @click="selectedFridgeId = fridge.id"
          >
            <div class="fridge-head">
              <strong>{{ fridge.code }}</strong>
              <span>{{ fridge.name }}</span>
              <StatusTag :status="fridge.status" type="success" />
            </div>
            <div class="fridge-metrics">
              <span><b>{{ fridge.in_stock }}</b> 在库</span>
              <span class="danger"><b>{{ fridge.expiring }}</b> 临期</span>
              <span class="muted"><b>{{ fridge.expired }}</b> 过期</span>
            </div>
            <el-progress :percentage="Math.min(fridge.usage, 100)" :show-text="false" :stroke-width="6" :color="fridge.usage > 85 ? '#DC2626' : '#2563EB'" />
            <small>{{ fridge.physical_count }} / {{ fridge.capacity }} 袋 · 使用率 {{ fridge.usage }}%</small>
          </button>
        </div>

        <div v-if="selectedFridge" class="fridge-detail">
          <div class="fridge-detail-head">
            <div>
              <h3>{{ selectedFridge.code }} · {{ selectedFridge.name }}</h3>
              <p>{{ selectedFridge.location }} · 在库 {{ selectedFridge.in_stock }} 袋 · 临期 {{ selectedFridge.expiring }} 袋 · 过期 {{ selectedFridge.expired }} 袋</p>
            </div>
            <div class="expiry-legend">
              <span><i class="ok" />>7 天</span>
              <span><i class="warning" />3–7 天</span>
              <span><i class="danger" />≤3 天</span>
              <span><i class="expired" />已过期</span>
            </div>
          </div>
          <div v-if="selectedFridge.bags.length" class="bag-grid">
            <el-tooltip v-for="bag in selectedFridge.bags" :key="bag.id" :content="cellTitle(bag)" placement="top" :show-after="150">
              <button type="button" class="bag-cell" :class="cellClass(bag)" @click="openDetail(bag)">
                <span class="bag-cell-no">{{ bag.bag_no.slice(-5) }}</span>
                <BloodBadge :type="bag.blood_type" :size="18" />
              </button>
            </el-tooltip>
          </div>
          <div v-else class="fridge-empty">该冰箱暂无在库血袋</div>
          <div class="fridge-foot">该冰箱共 {{ selectedFridge.physical_count }} 袋，其中 {{ selectedFridge.expiring }} 袋临期</div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="detailVisible" title="血袋详情" size="640px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="detail-hero">
            <div class="detail-blood"><BloodBadge :type="detail.blood_type" :size="46" /><RhTag :rh="detail.rh" /></div>
            <div>
              <h2>{{ detail.bag_no }}</h2>
              <p>{{ detail.product_name }} · {{ detail.specification }} · {{ detail.quantity }}{{ detail.product_name === '血浆' ? 'ml' : 'U' }}</p>
            </div>
            <div class="detail-tags">
              <StatusTag :status="detail.status" />
              <el-tag v-if="detail.has_adverse" type="danger" effect="light">曾发生不良反应</el-tag>
            </div>
          </div>
          <ExpiryBar :expiry-date="detail.expiry_date" :days="detail.days_to_expiry" :level="detail.expiry_level" :status="detail.status" />
          <div class="detail-grid detail-block">
            <div class="detail-item"><span class="label">来源血站</span><span class="value">{{ detail.source }}</span></div>
            <div class="detail-item"><span class="label">采血单位</span><span class="value">{{ detail.collection_unit }}</span></div>
            <div class="detail-item"><span class="label">献血者编号</span><span class="value">{{ detail.donor_no }}</span></div>
            <div class="detail-item"><span class="label">采血日期</span><span class="value">{{ detail.collection_date }}</span></div>
            <div class="detail-item"><span class="label">存放冰箱</span><span class="value">{{ detail.fridge_code }} {{ detail.fridge_name }}</span></div>
            <div class="detail-item"><span class="label">包装</span><span class="value">{{ detail.package }}</span></div>
            <div class="detail-item"><span class="label">入库人</span><span class="value">{{ detail.created_by }}</span></div>
            <div class="detail-item"><span class="label">入库时间</span><span class="value">{{ formatDateTime(detail.created_at) }}</span></div>
          </div>
          <h3 class="section-title">复检结果</h3>
          <div class="retest-list">
            <span v-for="(value, key) in detail.retest_result" :key="key" :class="{ fail: value === '不合格' }">{{ key }}：{{ value }}</span>
          </div>
          <h3 class="section-title">相关记录</h3>
          <el-timeline v-if="detail.cross_matches?.length || detail.adverse_reactions?.length || detail.scrap_records?.length">
            <el-timeline-item v-for="match in detail.cross_matches" :key="`m-${match.id}`" :timestamp="formatDateTime(match.matched_at)" :color="match.compatibility === '不相容' ? '#DC2626' : '#059669'">
              配血 {{ match.compatibility }} · {{ match.method }} · {{ match.technician }}
            </el-timeline-item>
            <el-timeline-item v-for="reaction in detail.adverse_reactions" :key="`a-${reaction.id}`" :timestamp="formatDateTime(reaction.occurred_at)" color="#D97706">
              不良反应 {{ reaction.reaction_type }} · {{ reaction.severity }} · {{ reaction.treatment }}
            </el-timeline-item>
            <el-timeline-item v-for="scrap in detail.scrap_records" :key="`s-${scrap.id}`" :timestamp="formatDateTime(scrap.applied_at)" color="#64748B">
              报废 {{ scrap.approval_status }} · {{ scrap.reason }}
            </el-timeline-item>
          </el-timeline>
          <div v-else class="muted">暂无相关记录</div>
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="scrapVisible" title="提交报废申请" width="480px">
      <el-form label-width="82px">
        <el-form-item label="血袋数量">{{ scrapForm.bag_ids.length }} 袋</el-form-item>
        <el-form-item label="报废原因" required>
          <el-input v-model="scrapForm.reason" type="textarea" :rows="4" placeholder="请填写报废原因，如过期、外观破损、复检异常等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scrapVisible = false">取消</el-button>
        <el-button type="primary" :loading="scrapLoading" @click="submitScrap">提交申请</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stock-tabs :deep(.el-tabs__content) {
  padding-top: 6px;
}

.bag-no {
  color: var(--bb-primary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.blood-cell {
  display: flex;
  gap: 5px;
  align-items: center;
}

.fridge-cards {
  display: flex;
  gap: 12px;
  padding-bottom: 16px;
  overflow-x: auto;
}

.fridge-card {
  flex: 0 0 240px;
  min-width: 240px;
  padding: 14px;
  text-align: left;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 6px;
  cursor: pointer;
}

.fridge-card:hover,
.fridge-card.active {
  background: #eff6ff;
  border-color: #2563eb;
}

html.dark .fridge-card:hover,
html.dark .fridge-card.active {
  background: #1e3a5f;
}

.fridge-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.fridge-head strong {
  color: var(--bb-primary);
  font-size: 16px;
}

.fridge-head span:nth-child(2) {
  flex: 1;
  color: var(--bb-text);
  font-size: 12px;
}

.fridge-metrics {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.fridge-metrics b {
  color: var(--bb-text);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.fridge-metrics .danger b {
  color: var(--bb-danger);
}

.fridge-card small {
  display: block;
  margin-top: 8px;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.fridge-detail {
  padding: 16px;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 6px;
}

.fridge-detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.fridge-detail-head h3 {
  margin: 0;
  font-size: 14px;
}

.fridge-detail-head p {
  margin: 5px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.expiry-legend {
  display: flex;
  gap: 10px;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.expiry-legend span {
  display: flex;
  gap: 4px;
  align-items: center;
}

.expiry-legend i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.expiry-legend i.ok {
  background: #059669;
}

.expiry-legend i.warning {
  background: #d97706;
}

.expiry-legend i.danger {
  background: #dc2626;
}

.expiry-legend i.expired {
  background: #94a3b8;
}

.bag-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 56px);
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.bag-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  padding: 3px;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 150ms ease-out, border-color 150ms ease-out;
}

.bag-cell:hover {
  border-color: var(--bb-primary);
  transform: translateY(-1px);
}

.bag-cell-no {
  font-size: 9px;
  font-variant-numeric: tabular-nums;
}

.cell-ok {
  color: #065f46;
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.cell-warning {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.cell-danger {
  color: #991b1b;
  background: #fef2f2;
  border-color: #fecaca;
}

.cell-expired {
  color: #64748b;
  text-decoration: line-through;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.fridge-empty {
  padding: 44px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  text-align: center;
}

.fridge-foot {
  padding-top: 12px;
  margin-top: 14px;
  color: var(--bb-text-secondary);
  font-size: 11px;
  border-top: 1px solid var(--bb-border);
}

.detail-hero {
  display: flex;
  gap: 12px;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--bb-border);
}

.detail-blood {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.detail-hero h2 {
  margin: 0;
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.detail-hero p {
  margin: 5px 0 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.detail-tags {
  display: flex;
  gap: 6px;
  margin-left: auto;
}

.detail-block {
  margin-top: 16px;
}

.retest-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.retest-list span {
  padding: 5px 9px;
  color: #065f46;
  font-size: 11px;
  background: #ecfdf5;
  border-radius: 4px;
}

.retest-list span.fail {
  color: #991b1b;
  background: #fef2f2;
}
</style>
