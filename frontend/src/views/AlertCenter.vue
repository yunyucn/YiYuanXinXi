<script setup>
/**
 * 预警中心：仅技师、主任和管理员可访问。
 *
 * 页面负责筛选、手动扫描、预警处理及扫描日志展示，权限由路由和后端双重校验。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Check, Refresh, Search, Timer, Warning } from '@element-plus/icons-vue'
import { alertApi } from '@/api'
import { useAppStore } from '@/store/app'
import { useAuthStore } from '@/store/auth'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const appStore = useAppStore()
const auth = useAuthStore()
const activeTab = ref('alerts')
const loading = ref(false)
const scanning = ref(false)
const alerts = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const scanInfo = ref({ last_scan: null, next_scan: null, interval_minutes: 10, logs: [] })
const handleVisible = ref(false)
/** 当前角色是否可处置预警：主任仅查看与督办，处理动作归输血科技师。 */
const canHandle = computed(() => auth.canAccess('alertsHandle'))
const handleTarget = ref(null)
const handleNote = ref('')
const handling = ref(false)

const filters = reactive({ type: '', level: '', handled: '' })
const alertTypes = ['临期', '过期', '低库存', '待配血超时', '复检未完成']
const levels = ['严重', '警告', '提示']

/** 当前页未处理预警数量。 */
const unhandledCount = computed(() => alerts.value.filter((item) => !item.is_handled).length)

/** 将预警类型映射为标签颜色。 */
function typeTag(type) {
  return {
    临期: 'warning',
    过期: 'danger',
    低库存: 'danger',
    待配血超时: 'warning',
    复检未完成: 'info',
  }[type] || 'info'
}

/** 将预警级别映射为标签颜色。 */
function levelTag(level) {
  return { 严重: 'danger', 警告: 'warning', 提示: 'info' }[level] || 'info'
}

/** 按未处理状态和级别返回行样式。 */
function levelRowClass({ row }) {
  if (row.is_handled) return 'handled-row'
  if (row.level === '严重') return 'danger-row'
  if (row.level === '警告') return 'warning-row'
  return ''
}

/** 加载当前筛选条件下的预警分页数据。 */
async function loadAlerts() {
  const data = await alertApi.list({
    type: filters.type || undefined,
    level: filters.level || undefined,
    handled: filters.handled || undefined,
    page: page.value,
    page_size: pageSize.value,
  })
  alerts.value = data.items
  total.value = data.total
}

/** 加载最近扫描记录和下次扫描时间。 */
async function loadLogs() {
  scanInfo.value = await alertApi.scanLogs()
}

/** 并行刷新预警、扫描日志和顶栏角标。 */
async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadAlerts(), loadLogs(), appStore.fetchAlertSummary()])
  } finally {
    loading.value = false
  }
}

/** 手动触发预警扫描，并刷新页面和角标。 */
async function refreshScan() {
  scanning.value = true
  try {
    const result = await alertApi.refresh()
    ElMessage.success(`扫描完成：新增 ${result.new_alerts} 条预警，${result.expired_bags} 袋血自动过期`)
    await Promise.all([loadAlerts(), loadLogs(), appStore.fetchAlertSummary(true)])
  } finally {
    scanning.value = false
  }
}

/** 筛选后回到第一页查询。 */
function search() {
  page.value = 1
  loadAlerts()
}

/** 重置预警筛选条件。 */
function resetFilters() {
  filters.type = ''
  filters.level = ''
  filters.handled = ''
  page.value = 1
  loadAlerts()
}

/** 打开预警处理弹窗。 */
function openHandle(row) {
  handleTarget.value = row
  handleNote.value = ''
  handleVisible.value = true
}

/** 提交处理备注并刷新预警摘要。 */
async function submitHandle() {
  if (!handleNote.value.trim()) {
    ElMessage.warning('请填写处理备注')
    return
  }
  handling.value = true
  try {
    await alertApi.handle(handleTarget.value.id, { note: handleNote.value.trim() })
    ElMessage.success('预警已标记处理')
    handleVisible.value = false
    await Promise.all([loadAlerts(), appStore.fetchAlertSummary()])
  } finally {
    handling.value = false
  }
}

/** 跳转到预警关联的血袋或申请单页面。 */
function openRelated(row) {
  if (row.link) router.push(row.link)
}

/** 根据处理状态生成操作列配置。 */
function alertActions(row) {
  if (!row.is_handled && canHandle.value) return [{ label: '处理', icon: Check, emphasis: true, onClick: () => openHandle(row) }]
  if (!row.is_handled) return [{ label: '待处理', type: 'warning', onClick: () => ElMessage.info('预警由输血科技师处置') }]
  return [
    {
      label: '详情',
      type: 'info',
      tooltip: row.handle_note || '已处理',
      onClick: () => ElMessage.info(row.handle_note || '该预警已处理'),
    },
  ]
}

onMounted(loadAll)
</script>

<template>
  <div class="page">
    <PageHeader
      title="预警中心"
      :description="canHandle ? '定时扫描临期、过期、低库存、待配血超时与复检未完成风险，警告与严重预警计入铃铛红点' : '查看并督办各类预警，处置动作由输血科技师执行'"
    >
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
        <el-button v-if="canHandle" type="primary" :icon="Warning" :loading="scanning" @click="refreshScan">立即扫描</el-button>
      </template>
    </PageHeader>

    <div class="scan-overview">
      <div class="page-card scan-item tone-blue">
        <DecorPattern variant="cross" tone="blue" class="scan-decor" />
        <span class="scan-icon"><el-icon :size="20"><Timer /></el-icon></span>
        <div><span>上次扫描</span><strong>{{ formatDateTime(scanInfo.last_scan) }}</strong></div>
      </div>
      <div class="page-card scan-item tone-teal">
        <DecorPattern variant="pulse" tone="teal" class="scan-decor" />
        <span class="scan-icon"><el-icon :size="20"><Timer /></el-icon></span>
        <div><span>下次扫描</span><strong>{{ formatDateTime(scanInfo.next_scan) }}</strong></div>
      </div>
      <div class="page-card scan-item tone-amber">
        <DecorPattern variant="cells" tone="amber" class="scan-decor" />
        <span class="scan-icon warning"><el-icon :size="20"><Bell /></el-icon></span>
        <div><span>铃铛红点</span><strong>{{ appStore.alertCount }} 条</strong></div>
      </div>
      <div class="page-card scan-item tone-rose">
        <DecorPattern variant="pulse" tone="rose" class="scan-decor" />
        <span class="scan-icon danger"><el-icon :size="20"><Warning /></el-icon></span>
        <div><span>当前页未处理</span><strong>{{ unhandledCount }} 条</strong></div>
      </div>
    </div>

    <section class="page-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="预警列表" name="alerts">
          <div class="filter-bar">
            <el-select v-model="filters.type" clearable placeholder="预警类型" style="width: 150px" @change="search">
              <el-option v-for="item in alertTypes" :key="item" :label="item" :value="item" />
            </el-select>
            <el-select v-model="filters.level" clearable placeholder="预警级别" style="width: 130px" @change="search">
              <el-option v-for="item in levels" :key="item" :label="item" :value="item" />
            </el-select>
            <el-select v-model="filters.handled" clearable placeholder="处理状态" style="width: 130px" @change="search">
              <el-option label="未处理" value="0" />
              <el-option label="已处理" value="1" />
            </el-select>
            <el-button type="primary" :icon="Search" @click="search">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
            <span class="hint-text">提示级预警不计入铃铛红点，但仍需关注复检进度。</span>
          </div>

          <el-table v-loading="loading" :data="alerts" border :row-class-name="levelRowClass">
            <el-table-column label="类型" width="124">
              <template #default="{ row }"><el-tag :type="typeTag(row.type)" size="small" effect="light">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column label="级别" width="88">
              <template #default="{ row }"><el-tag :type="levelTag(row.level)" size="small" effect="light">{{ row.level }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="content" label="预警内容" min-width="420" show-overflow-tooltip />
            <el-table-column label="关联对象" width="150">
              <template #default="{ row }">
                <el-button v-if="row.related_label" text type="primary" @click="openRelated(row)">{{ row.related_label }}</el-button>
                <span v-else class="muted">{{ row.related_type }}</span>
              </template>
            </el-table-column>
            <el-table-column label="生成时间" width="158">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="92">
              <template #default="{ row }"><el-tag :type="row.is_handled ? 'info' : 'warning'" size="small">{{ row.is_handled ? '已处理' : '未处理' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="96" fixed="right" align="center">
              <template #default="{ row }"><TableActions :actions="alertActions(row)" /></template>
            </el-table-column>
          </el-table>

          <div class="table-footer">
            <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadAlerts" @size-change="loadAlerts" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="扫描日志" name="logs">
          <div class="log-tip">系统每 {{ scanInfo.interval_minutes }} 分钟自动扫描一次，应用启动时也会立即执行一次扫描。</div>
          <el-table :data="scanInfo.logs" border>
            <el-table-column prop="scanned_at" label="扫描时间" min-width="180">
              <template #default="{ row }">{{ formatDateTime(row.scanned_at) }}</template>
            </el-table-column>
            <el-table-column prop="trigger_type" label="触发方式" width="110">
              <template #default="{ row }"><el-tag :type="row.trigger_type === '手动' ? 'primary' : 'info'" size="small">{{ row.trigger_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="new_alerts" label="新增预警" width="110" align="right" />
            <el-table-column prop="expired_bags" label="自动过期血袋" width="130" align="right" />
            <el-table-column prop="cost_ms" label="耗时（ms）" width="120" align="right" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="handleVisible" title="处理预警" width="520px">
      <div v-if="handleTarget" class="handle-summary">
        <div><el-tag :type="typeTag(handleTarget.type)">{{ handleTarget.type }}</el-tag><el-tag :type="levelTag(handleTarget.level)">{{ handleTarget.level }}</el-tag></div>
        <p>{{ handleTarget.content }}</p>
        <span>{{ handleTarget.related_label || handleTarget.related_type }} · {{ formatDateTime(handleTarget.created_at) }}</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="处理备注">
          <el-input v-model="handleNote" type="textarea" :rows="4" placeholder="如：已安排优先使用、已补充库存、已联系临床科室等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" :loading="handling" @click="submitHandle">确认处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.scan-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.scan-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  overflow: hidden;
}

.scan-item > *:not(.scan-decor) {
  position: relative;
  z-index: 1;
}

.scan-decor {
  right: 0;
  left: auto;
  width: 44%;
  opacity: 0.14;
  mask-image: linear-gradient(90deg, transparent 0%, #000 55%, #000 100%);
}

.scan-item.tone-blue {
  background: radial-gradient(110% 100% at 100% 0%, rgba(56, 189, 248, 0.03), transparent 60%), linear-gradient(180deg, #ffffff, var(--bb-card) 80%);
}

.scan-item.tone-teal {
  background: radial-gradient(110% 100% at 100% 0%, rgba(13, 148, 136, 0.028), transparent 60%), linear-gradient(180deg, #ffffff, var(--bb-card) 80%);
}

.scan-item.tone-amber {
  background: radial-gradient(110% 100% at 100% 0%, rgba(217, 119, 6, 0.03), transparent 60%), linear-gradient(180deg, #ffffff, var(--bb-card) 80%);
}

.scan-item.tone-rose {
  background: radial-gradient(110% 100% at 100% 0%, rgba(220, 38, 38, 0.028), transparent 60%), linear-gradient(180deg, #ffffff, var(--bb-card) 80%);
}

.scan-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: var(--bb-primary);
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 5px;
}

.scan-icon.warning {
  color: var(--bb-warning);
  background: #fffbeb;
  border-color: #fde68a;
}

.scan-icon.danger {
  color: var(--bb-danger);
  background: #fef2f2;
  border-color: #fecaca;
}

.scan-item span,
.scan-item strong {
  display: block;
}

.scan-item div > span {
  margin-bottom: 4px;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.scan-item strong {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.hint-text {
  margin-left: auto;
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.log-tip {
  padding: 10px 12px;
  margin-bottom: 14px;
  color: #1d4ed8;
  font-size: 11px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.handle-summary {
  padding: 12px 14px;
  margin-bottom: 16px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.handle-summary > div {
  display: flex;
  gap: 7px;
}

.handle-summary p {
  margin: 9px 0 5px;
  font-size: 12px;
  line-height: 1.6;
}

.handle-summary span {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

:deep(.handled-row) {
  color: #94a3b8;
}

:deep(.danger-row td:first-child) {
  box-shadow: inset 3px 0 0 var(--bb-danger);
}

:deep(.warning-row td:first-child) {
  box-shadow: inset 3px 0 0 var(--bb-warning);
}
</style>
