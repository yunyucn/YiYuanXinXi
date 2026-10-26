<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FirstAidKit, Printer, Refresh, Search, Warning } from '@element-plus/icons-vue'
import { adverseApi, issueApi } from '@/api'
import { formatDateTime } from '@/utils/format'

const activeTab = ref('pending')
const loading = ref(false)
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const executingId = ref(null)
const adverseVisible = ref(false)
const adverseSubmitting = ref(false)
const adverseIssue = ref(null)

const adverseForm = reactive({
  bag_id: null,
  reaction_type: '发热',
  severity: '轻度',
  occurred_at: '',
  treatment: '',
  reported_to_station: false,
  note: '',
})

const reactionTypes = ['发热', '过敏', '溶血', '其他']
const severities = ['轻度', '中度', '重度']
const tabStatus = computed(() => (activeTab.value === 'pending' ? '待执行' : '已完成'))

function nowDateTime() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 19)
}

async function loadIssues() {
  loading.value = true
  try {
    const data = await issueApi.list({
      execution_status: tabStatus.value,
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    records.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  loadIssues()
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

async function execute(row) {
  await ElMessageBox.confirm(
    `确认已为患者 ${row.patient_name}（${row.admission_no}）完成输血执行？确认后申请单将转为已完成。`,
    '输血执行确认',
    { type: 'warning', confirmButtonText: '确认执行' },
  )
  executingId.value = row.id
  try {
    await issueApi.execute(row.id)
    ElMessage.success('输血执行已确认')
    await loadIssues()
    await openDetail(row)
  } finally {
    executingId.value = null
  }
}

async function openAdverse(row) {
  adverseIssue.value = row
  if (!row.bags?.length) {
    adverseIssue.value = await issueApi.detail(row.id)
  }
  Object.assign(adverseForm, {
    bag_id: adverseIssue.value.bags?.[0]?.id || null,
    reaction_type: '发热',
    severity: '轻度',
    occurred_at: nowDateTime(),
    treatment: '',
    reported_to_station: false,
    note: '',
  })
  adverseVisible.value = true
}

async function submitAdverse() {
  if (!adverseForm.bag_id) {
    ElMessage.warning('请选择发生不良反应的血袋')
    return
  }
  if (!adverseForm.treatment.trim()) {
    ElMessage.warning('请填写处理措施')
    return
  }
  adverseSubmitting.value = true
  try {
    await adverseApi.create({
      issue_record_id: adverseIssue.value.id,
      bag_id: adverseForm.bag_id,
      reaction_type: adverseForm.reaction_type,
      severity: adverseForm.severity,
      occurred_at: adverseForm.occurred_at,
      treatment: adverseForm.treatment,
      reported_to_station: adverseForm.reported_to_station,
      note: adverseForm.note,
    })
    ElMessage.success('不良反应已上报')
    adverseVisible.value = false
    if (detailVisible.value && detail.value?.id === adverseIssue.value.id) {
      detail.value = await issueApi.detail(adverseIssue.value.id)
    }
  } finally {
    adverseSubmitting.value = false
  }
}

function printRecord(id) {
  window.open(`/print/record/${id}`, '_blank')
}

function executeActions(row) {
  return [
    { label: '详情', onClick: () => openDetail(row) },
    activeTab.value === 'pending'
      ? {
          label: '确认执行',
          icon: FirstAidKit,
          loading: executingId.value === row.id,
          onClick: () => execute(row),
        }
      : { label: '上报反应', type: 'warning', icon: Warning, onClick: () => openAdverse(row) },
    { label: '记录单', icon: Printer, onClick: () => printRecord(row.id) },
  ]
}

watch(activeTab, () => {
  page.value = 1
  keyword.value = ''
  loadIssues()
})

onMounted(loadIssues)
</script>

<template>
  <div class="page">
    <PageHeader title="输血执行" description="护士确认输血执行，并在完成后记录输血不良反应；执行时间与记录护士将进入全周期追溯">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="loadIssues">刷新</el-button>
      </template>
    </PageHeader>

    <section class="page-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="待执行" name="pending" />
        <el-tab-pane label="已完成" name="completed" />
      </el-tabs>

      <div class="filter-bar">
        <el-input v-model="keyword" :prefix-icon="Search" clearable placeholder="记录号 / 申请单号 / 患者姓名" style="width: 300px" @keyup.enter="search" />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button @click="keyword = ''; search()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="records" border>
        <el-table-column prop="record_no" label="发血记录号" min-width="180">
          <template #default="{ row }"><span class="record-no">{{ row.record_no }}</span></template>
        </el-table-column>
        <el-table-column prop="patient_name" label="患者" width="100" />
        <el-table-column prop="admission_no" label="住院号" width="130" />
        <el-table-column prop="department" label="科室" width="110" />
        <el-table-column prop="bed_no" label="床号" width="78" />
        <el-table-column prop="product_name" label="品种" min-width="112" />
        <el-table-column label="血袋" width="76" align="center">
          <template #default="{ row }">{{ row.bags?.length || 0 }} 袋</template>
        </el-table-column>
        <el-table-column prop="pickup_nurse" label="领血护士" width="100" />
        <el-table-column label="发血时间" width="158">
          <template #default="{ row }">{{ formatDateTime(row.issued_at) }}</template>
        </el-table-column>
        <el-table-column v-if="activeTab === 'completed'" label="执行时间" width="158">
          <template #default="{ row }">{{ formatDateTime(row.executed_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="92">
          <template #default="{ row }"><StatusTag :status="row.execution_status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right" align="center">
          <template #default="{ row }"><TableActions :actions="executeActions(row)" /></template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadIssues" @size-change="loadIssues" />
      </div>
    </section>

    <el-drawer v-model="detailVisible" title="输血执行详情" size="760px">
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
            <div class="detail-item"><span class="label">领血护士</span><span class="value">{{ detail.pickup_nurse }}</span></div>
            <div class="detail-item"><span class="label">发血人</span><span class="value">{{ detail.issued_by }}</span></div>
            <div class="detail-item"><span class="label">发血时间</span><span class="value">{{ formatDateTime(detail.issued_at) }}</span></div>
            <div class="detail-item"><span class="label">执行护士</span><span class="value">{{ detail.executed_by || '-' }}</span></div>
            <div class="detail-item"><span class="label">执行时间</span><span class="value">{{ formatDateTime(detail.executed_at) }}</span></div>
          </div>

          <h3 class="section-title">血袋与配血</h3>
          <el-table :data="detail.bags" border size="small">
            <el-table-column prop="bag_no" label="储血号" min-width="132" />
            <el-table-column label="血型" width="84">
              <template #default="{ row }"><BloodBadge :type="row.blood_type" :size="22" /></template>
            </el-table-column>
            <el-table-column label="Rh" width="82">
              <template #default="{ row }"><RhTag :rh="row.rh" /></template>
            </el-table-column>
            <el-table-column prop="product_name" label="品种" min-width="110" />
            <el-table-column prop="quantity" label="数量" width="72" align="right" />
            <el-table-column label="配血结果" width="96">
              <template #default="{ row }">
                <el-tag :type="detail.cross_matches?.some((item) => item.bag_id === row.id && item.compatibility === '相容') ? 'success' : 'info'" size="small">
                  {{ detail.cross_matches?.some((item) => item.bag_id === row.id && item.compatibility === '相容') ? '相容' : '未记录' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>

          <h3 class="section-title">发血核对项</h3>
          <div class="check-tags">
            <el-tag v-for="item in detail.check_items" :key="item" type="success" effect="light">{{ item }}</el-tag>
          </div>

          <div class="adverse-head">
            <h3 class="section-title">不良反应</h3>
            <el-button v-if="detail.execution_status === '已完成'" size="small" type="warning" :icon="Warning" @click="openAdverse(detail)">上报不良反应</el-button>
          </div>
          <div v-if="detail.adverse_reactions?.length" class="reaction-list">
            <div v-for="item in detail.adverse_reactions" :key="item.id" class="reaction-card">
              <div>
                <el-tag type="warning">{{ item.reaction_type }}</el-tag>
                <el-tag type="danger" effect="plain">{{ item.severity }}</el-tag>
                <strong>{{ item.bag_no }}</strong>
                <span>{{ formatDateTime(item.occurred_at) }}</span>
              </div>
              <p>{{ item.treatment }}</p>
              <small>记录护士：{{ item.nurse }} · {{ item.reported_to_station ? '已上报血站' : '未上报血站' }}</small>
            </div>
          </div>
          <el-empty v-else :image-size="58" description="暂无不良反应记录" />

          <div class="drawer-actions">
            <el-button @click="detailVisible = false">关闭</el-button>
            <el-button type="primary" :icon="Printer" @click="printRecord(detail.id)">打印输血记录单</el-button>
            <el-button v-if="detail.execution_status === '待执行'" type="success" :icon="FirstAidKit" :loading="executingId === detail.id" @click="execute(detail)">确认执行</el-button>
          </div>
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="adverseVisible" title="上报输血不良反应" width="600px" destroy-on-close>
      <div v-if="adverseIssue" class="dialog-patient">
        <strong>{{ adverseIssue.patient_name }}</strong>
        <span>{{ adverseIssue.admission_no }} · {{ adverseIssue.record_no }}</span>
      </div>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="发生血袋">
              <el-select v-model="adverseForm.bag_id" style="width: 100%">
                <el-option v-for="bag in adverseIssue?.bags || []" :key="bag.id" :label="`${bag.bag_no} · ${bag.product_name}`" :value="bag.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发生时间">
              <el-date-picker v-model="adverseForm.occurred_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="反应类型">
              <el-radio-group v-model="adverseForm.reaction_type">
                <el-radio-button v-for="item in reactionTypes" :key="item" :value="item">{{ item }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="反应程度">
              <el-radio-group v-model="adverseForm.severity">
                <el-radio-button v-for="item in severities" :key="item" :value="item">{{ item }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="处理措施">
          <el-input v-model="adverseForm.treatment" type="textarea" :rows="3" placeholder="如：减慢滴速、停止输血、给予抗过敏治疗等" />
        </el-form-item>
        <el-form-item label="补充说明">
          <el-input v-model="adverseForm.note" type="textarea" :rows="2" placeholder="生命体征、症状变化等（可选）" />
        </el-form-item>
        <el-form-item label="是否已上报血站">
          <el-switch v-model="adverseForm.reported_to_station" active-text="已上报" inactive-text="未上报" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adverseVisible = false">取消</el-button>
        <el-button type="warning" :loading="adverseSubmitting" @click="submitAdverse">提交上报</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.record-no,
.eyebrow {
  color: var(--bb-primary);
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--bb-border);
}

.detail-hero h2 {
  margin: 6px 0 5px;
  font-size: 23px;
}

.detail-hero h2 small {
  margin-left: 8px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.detail-hero p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.check-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

.adverse-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
}

.adverse-head .section-title {
  margin-bottom: 10px;
}

.reaction-list {
  display: grid;
  gap: 9px;
}

.reaction-card {
  padding: 11px 13px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 5px;
}

.reaction-card > div {
  display: flex;
  gap: 7px;
  align-items: center;
}

.reaction-card strong {
  font-size: 12px;
}

.reaction-card span,
.reaction-card small {
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.reaction-card p {
  margin: 8px 0 5px;
  color: var(--bb-text);
  font-size: 12px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid var(--bb-border);
}

.dialog-patient {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 10px 12px;
  margin-bottom: 16px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 5px;
}

.dialog-patient span {
  color: var(--bb-text-secondary);
  font-size: 11px;
}
</style>
