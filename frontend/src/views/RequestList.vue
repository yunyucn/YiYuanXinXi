<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { requestApi, systemApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import { formatDateTime, urgencyType } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const products = ref([])
const departments = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)
const submitting = ref(false)
const detailVisible = ref(false)
const detail = ref(null)
const detailLoading = ref(false)

const filters = reactive({ status: '', urgency: '', keyword: '' })
const form = reactive({
  patient_name: '',
  admission_no: '',
  department: '',
  bed_no: '',
  blood_type: 'A',
  rh: 'D阳性',
  diagnosis: '',
  product_name: '',
  quantity: 2,
  quantity_unit: 'U',
  urgency: '常规',
})

const statuses = ['待配血', '配血中', '已备血', '已发血', '已完成', '已取消']
const bloodTypes = ['A', 'B', 'AB', 'O']
const urgencies = ['常规', '紧急', '抢救']
const canCreate = computed(() => auth.canAccess('requestCreate'))
const productMap = computed(() => Object.fromEntries(products.value.map((item) => [item.name, item])))
const rules = {
  patient_name: [{ required: true, message: '请输入患者姓名', trigger: 'blur' }],
  admission_no: [{ required: true, message: '请输入住院号', trigger: 'blur' }],
  department: [{ required: true, message: '请选择科室', trigger: 'change' }],
  blood_type: [{ required: true, message: '请选择血型', trigger: 'change' }],
  diagnosis: [{ required: true, message: '请输入临床诊断', trigger: 'blur' }],
  product_name: [{ required: true, message: '请选择申请品种', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入申请量', trigger: 'blur' }],
}

async function loadRequests() {
  loading.value = true
  try {
    const data = await requestApi.list({ ...filters, page: page.value, page_size: pageSize.value })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  loadRequests()
}

function resetFilters() {
  Object.assign(filters, { status: '', urgency: '', keyword: '' })
  search()
}

function onProductChange(name) {
  const product = productMap.value[name]
  if (!product) return
  form.quantity_unit = product.unit
  form.quantity = product.unit === 'ml' ? 400 : product.name === '全血' ? 1.5 : 2
}

function openCreate() {
  Object.assign(form, {
    patient_name: '',
    admission_no: '',
    department: departments.value[0]?.name || '',
    bed_no: '',
    blood_type: 'A',
    rh: 'D阳性',
    diagnosis: '',
    product_name: products.value[0]?.name || '',
    quantity: 2,
    quantity_unit: products.value[0]?.unit || 'U',
    urgency: '常规',
  })
  dialogVisible.value = true
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    await requestApi.create(form)
    ElMessage.success('输血申请已提交，等待输血科配血')
    dialogVisible.value = false
    await loadRequests()
  } finally {
    submitting.value = false
  }
}

async function cancel(row) {
  await ElMessageBox.confirm(`确认取消申请单 ${row.request_no} 吗？`, '取消申请', { type: 'warning' })
  await requestApi.cancel(row.id, { reason: '申请医生取消' })
  ElMessage.success('申请已取消')
  loadRequests()
}

async function openDetail(rowOrId) {
  const id = typeof rowOrId === 'object' ? rowOrId.id : rowOrId
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await requestApi.detail(id)
  } finally {
    detailLoading.value = false
  }
}

function requestActions(row) {
  const actions = [
    { label: '详情', onClick: () => openDetail(row) },
    { label: '追溯', type: 'info', onClick: () => router.push(`/trace?admission_no=${row.admission_no}`) },
  ]
  if (canCreate.value && ['待配血', '配血中'].includes(row.status)) {
    actions.push({ label: '取消', type: 'danger', onClick: () => cancel(row) })
  }
  return actions
}

onMounted(async () => {
  const [productList, departmentList] = await Promise.all([systemApi.products(), systemApi.departments()])
  products.value = productList
  departments.value = departmentList
  await loadRequests()
  if (route.query.request_id) openDetail(Number(route.query.request_id))
})
</script>

<template>
  <div class="page">
    <PageHeader title="输血申请" description="临床医生提交输血申请，实时查看配血、发血与执行状态">
      <template #actions>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">新建申请</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadRequests">刷新</el-button>
      </template>
    </PageHeader>

    <div class="page-card">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="申请单号 / 患者 / 住院号" clearable style="width: 230px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filters.status" placeholder="申请状态" clearable style="width: 130px" @change="search">
          <el-option v-for="status in statuses" :key="status" :label="status" :value="status" />
        </el-select>
        <el-select v-model="filters.urgency" placeholder="紧急程度" clearable style="width: 120px" @change="search">
          <el-option v-for="urgency in urgencies" :key="urgency" :label="urgency" :value="urgency" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="items" border height="520">
        <el-table-column prop="request_no" label="申请单号" min-width="150" fixed>
          <template #default="{ row }"><span class="request-no clickable" @click="openDetail(row)">{{ row.request_no }}</span></template>
        </el-table-column>
        <el-table-column prop="patient_name" label="患者" width="90" />
        <el-table-column prop="admission_no" label="住院号" min-width="125" />
        <el-table-column label="科室/床号" min-width="115">
          <template #default="{ row }">{{ row.department }} {{ row.bed_no }}</template>
        </el-table-column>
        <el-table-column label="血型" width="74">
          <template #default="{ row }"><div class="blood-inline"><BloodBadge :type="row.blood_type" :size="22" /><RhTag :rh="row.rh" /></div></template>
        </el-table-column>
        <el-table-column label="申请品种" width="105">
          <template #default="{ row }">{{ row.product_name }}</template>
        </el-table-column>
        <el-table-column label="申请量" width="90" align="right">
          <template #default="{ row }"><span class="tabular">{{ row.quantity }}{{ row.quantity_unit }}</span></template>
        </el-table-column>
        <el-table-column label="紧急程度" width="90">
          <template #default="{ row }"><el-tag :type="urgencyType(row.urgency)" size="small" effect="light">{{ row.urgency }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column prop="doctor" label="申请医生" width="90" />
        <el-table-column label="申请时间" width="155">
          <template #default="{ row }">{{ formatDateTime(row.requested_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="156" fixed="right" align="center">
          <template #default="{ row }"><TableActions :actions="requestActions(row)" /></template>
        </el-table-column>
      </el-table>
      <div class="table-footer">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadRequests" @size-change="search" />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新建输血申请" width="800px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
        <el-row :gutter="18">
          <el-col :span="8"><el-form-item label="患者姓名" prop="patient_name"><el-input v-model="form.patient_name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="住院号" prop="admission_no"><el-input v-model="form.admission_no" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="科室" prop="department"><el-select v-model="form.department" style="width: 100%"><el-option v-for="item in departments" :key="item.id" :label="item.name" :value="item.name" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="18">
          <el-col :span="8"><el-form-item label="床号"><el-input v-model="form.bed_no" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="患者血型" prop="blood_type"><el-select v-model="form.blood_type" style="width: 100%"><el-option v-for="type in bloodTypes" :key="type" :label="type" :value="type" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="Rh"><el-select v-model="form.rh" style="width: 100%"><el-option label="D 阳性" value="D阳性" /><el-option label="D 阴性" value="D阴性" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="临床诊断" prop="diagnosis"><el-input v-model="form.diagnosis" type="textarea" :rows="2" placeholder="请输入诊断依据" /></el-form-item>
        <el-row :gutter="18">
          <el-col :span="8"><el-form-item label="申请品种" prop="product_name"><el-select v-model="form.product_name" style="width: 100%" @change="onProductChange"><el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.name" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="申请量" prop="quantity"><el-input-number v-model="form.quantity" :min="0.5" :step="0.5" :precision="1" controls-position="right" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="单位"><el-input v-model="form.quantity_unit" disabled /></el-form-item></el-col>
        </el-row>
        <el-form-item label="紧急程度"><el-radio-group v-model="form.urgency"><el-radio-button v-for="item in urgencies" :key="item" :value="item">{{ item }}</el-radio-button></el-radio-group></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">提交申请</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="申请单详情" size="640px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div class="request-hero">
            <div>
              <span class="muted">{{ detail.request_no }}</span>
              <h2>{{ detail.patient_name }} <small>{{ detail.admission_no }}</small></h2>
              <p>{{ detail.department }} {{ detail.bed_no }} · {{ detail.diagnosis }}</p>
            </div>
            <div class="hero-right">
              <div class="blood-inline"><BloodBadge :type="detail.blood_type" :size="34" /><RhTag :rh="detail.rh" /></div>
              <StatusTag :status="detail.status" />
            </div>
          </div>
          <div class="detail-grid">
            <div class="detail-item"><span class="label">申请品种</span><span class="value">{{ detail.product_name }}</span></div>
            <div class="detail-item"><span class="label">申请量</span><span class="value">{{ detail.quantity }}{{ detail.quantity_unit }}</span></div>
            <div class="detail-item"><span class="label">紧急程度</span><span class="value">{{ detail.urgency }}</span></div>
            <div class="detail-item"><span class="label">申请医生</span><span class="value">{{ detail.doctor }}</span></div>
            <div class="detail-item"><span class="label">申请时间</span><span class="value">{{ formatDateTime(detail.requested_at) }}</span></div>
            <div class="detail-item"><span class="label">取消原因</span><span class="value">{{ detail.cancel_reason || '-' }}</span></div>
          </div>
          <h3 class="section-title">配血记录</h3>
          <el-timeline v-if="detail.cross_matches?.length">
            <el-timeline-item v-for="match in detail.cross_matches" :key="match.id" :timestamp="formatDateTime(match.matched_at)" :color="match.compatibility === '不相容' ? '#DC2626' : '#059669'">
              {{ match.bag_no }} · {{ match.method }} · {{ match.compatibility }} · {{ match.technician }}
            </el-timeline-item>
          </el-timeline>
          <div v-else class="muted">尚未配血</div>
          <h3 class="section-title">发血记录</h3>
          <el-timeline v-if="detail.issue_records?.length">
            <el-timeline-item v-for="issue in detail.issue_records" :key="issue.id" :timestamp="formatDateTime(issue.issued_at)" color="#2563EB">
              {{ issue.record_no }} · {{ issue.execution_status }} · 领血护士 {{ issue.pickup_nurse }}
            </el-timeline-item>
          </el-timeline>
          <div v-else class="muted">尚未发血</div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.request-no {
  color: var(--bb-primary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.blood-inline {
  display: flex;
  gap: 5px;
  align-items: center;
}

.request-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--bb-border);
}

.request-hero h2 {
  margin: 5px 0;
  font-size: 22px;
}

.request-hero h2 small {
  margin-left: 8px;
  color: var(--bb-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.request-hero p {
  margin: 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.hero-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
