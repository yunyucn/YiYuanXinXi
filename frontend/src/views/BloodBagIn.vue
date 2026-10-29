<script setup>
/** 血液入库：支持单袋录入和批量录入，并展示品种对应的效期规则。 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Remove } from '@element-plus/icons-vue'
import { bagApi, systemApi } from '@/api'
import { addDays, todayString } from '@/utils/format'

const activeTab = ref('single')
const formRef = ref(null)
const loading = ref(false)
const products = ref([])
const fridges = ref([])

const retestLabels = [
  { key: 'blood_type', label: '定血型' },
  { key: 'rh', label: 'Rh' },
  { key: 'alt', label: 'ALT' },
  { key: 'hiv', label: 'HIV' },
  { key: 'syphilis', label: '梅毒' },
  { key: 'hbv', label: '乙肝' },
  { key: 'hcv', label: '丙肝' },
]

const retestOptions = ['合格', '不合格']
const bloodTypes = ['A', 'B', 'AB', 'O']
const rhOptions = ['D阳性', 'D阴性']

/** 生成七项复检默认合格结果。 */
function emptyRetest() {
  return Object.fromEntries(retestLabels.map((item) => [item.key, '合格']))
}

/** 生成单袋入库表单初始值。 */
function emptyBag() {
  return {
    product_name: '',
    blood_type: 'A',
    rh: 'D阳性',
    specification: '',
    quantity: 1,
    source: '市中心血站',
    collection_unit: '市中心血站',
    donor_no: '',
    collection_date: todayString(),
    package: '一次性血袋',
    fridge_id: null,
    is_autologous: false,
    retest_result: emptyRetest(),
  }
}

const single = reactive(emptyBag())
const batch = reactive({
  source: '市中心血站',
  collection_unit: '市中心血站',
  collection_date: todayString(),
  package: '一次性血袋',
  fridge_id: null,
  retest_result: emptyRetest(),
  items: [
    { product_name: '', blood_type: 'A', rh: 'D阳性', quantity: 1, donor_no: '' },
    { product_name: '', blood_type: 'B', rh: 'D阳性', quantity: 1, donor_no: '' },
    { product_name: '', blood_type: 'O', rh: 'D阳性', quantity: 1, donor_no: '' },
  ],
})

const rules = {
  product_name: [{ required: true, message: '请选择血液品种', trigger: 'change' }],
  donor_no: [{ required: true, message: '请输入献血者编号', trigger: 'blur' }],
  collection_date: [{ required: true, message: '请选择采血日期', trigger: 'change' }],
  fridge_id: [{ required: true, message: '入库必须选择冰箱', trigger: 'change' }],
}

/** 品种名称到字典对象的索引。 */
const productMap = computed(() => Object.fromEntries(products.value.map((item) => [item.name, item])))
/** 当前单袋表单选中的品种。 */
const singleProduct = computed(() => productMap.value[single.product_name])
/** 根据品种保质期预测有效期。 */
const singleExpiry = computed(() => (singleProduct.value ? addDays(single.collection_date, singleProduct.value.shelf_life_days) : '-'))

/** 品种变化时带出推荐规格和数量。 */
function onSingleProductChange(name) {
  const product = productMap.value[name]
  if (product) {
    single.specification = product.unit === 'ml' ? '200ml' : product.unit === 'U' ? '2U' : product.unit
    single.quantity = product.unit === 'ml' ? 200 : product.name === '全血' ? 1.5 : product.name === '悬浮红细胞' ? 2 : 1
  }
}

/** 计算批量录入行的预计有效期。 */
function rowExpiry(row) {
  const product = productMap.value[row.product_name]
  return product ? addDays(batch.collection_date, product.shelf_life_days) : '-'
}

/** 重置单袋表单及校验状态。 */
function resetSingle() {
  Object.assign(single, emptyBag())
  formRef.value?.clearValidate()
}

/** 校验并提交单袋入库；复检不合格时后端会转待审批报废。 */
async function submitSingle() {
  try {
    await formRef.value.validate()
  } catch {
    formRef.value?.$el?.classList.add('shake')
    window.setTimeout(() => formRef.value?.$el?.classList.remove('shake'), 320)
    return
  }
  loading.value = true
  try {
    const payload = {
      ...single,
      specification: single.specification || singleProduct.value?.unit,
    }
    await bagApi.create(payload)
    ElMessage.success('入库成功，有效期已按品种自动计算')
    resetSingle()
  } finally {
    loading.value = false
  }
}

/** 批量录入增加一行。 */
function addBatchRow() {
  batch.items.push({ product_name: '', blood_type: 'A', rh: 'D阳性', quantity: 1, donor_no: '' })
}

/** 删除批量录入指定行，至少保留一行。 */
function removeBatchRow(index) {
  if (batch.items.length <= 1) return
  batch.items.splice(index, 1)
}

/** 校验批量表单并一次性提交最多 20 条入库记录。 */
async function submitBatch() {
  if (!batch.fridge_id) {
    ElMessage.warning('批量入库必须选择存放冰箱')
    return
  }
  if (!batch.collection_date) {
    ElMessage.warning('请选择采血日期')
    return
  }
  const invalid = batch.items.findIndex((row) => !row.product_name || !row.donor_no || !row.quantity)
  if (invalid >= 0) {
    ElMessage.warning(`第 ${invalid + 1} 行信息不完整`)
    return
  }
  loading.value = true
  try {
    const items = batch.items.map((row) => {
      const product = productMap.value[row.product_name]
      return {
        ...row,
        specification: product?.unit === 'ml' ? '200ml' : product?.unit === 'U' ? '2U' : product?.unit,
        source: batch.source,
        collection_unit: batch.collection_unit,
        collection_date: batch.collection_date,
        package: batch.package,
        fridge_id: batch.fridge_id,
        retest_result: batch.retest_result,
      }
    })
    await bagApi.createBatch({ items })
    ElMessage.success(`批量入库成功，共 ${items.length} 袋`)
    batch.items = [{ product_name: '', blood_type: 'A', rh: 'D阳性', quantity: 1, donor_no: '' }]
  } finally {
    loading.value = false
  }
}

// 初始化品种和可用冰箱字典。
onMounted(async () => {
  const [productList, fridgeList] = await Promise.all([systemApi.products(), systemApi.fridges()])
  products.value = productList
  fridges.value = fridgeList.filter((item) => item.status === '正常')
})
</script>

<template>
  <div class="page">
    <PageHeader title="血液入库" description="录入血液制品信息，系统按品种保质期自动计算有效期，并强制校验复检结果与存放冰箱">
      <template #actions>
        <el-button :icon="Refresh" @click="activeTab === 'single' ? resetSingle() : null">重置</el-button>
      </template>
    </PageHeader>

    <div class="rule-strip">
      <span><strong>有效期规则</strong> 全血/红细胞 35 天 · 血浆/冷沉淀 365 天 · 血小板 5 天</span>
      <span><strong>复检要求</strong> 7 项复检结果完整；不合格将转入待审批报废，不进入库存</span>
    </div>

    <el-tabs v-model="activeTab" class="page-card">
      <el-tab-pane label="单袋入库" name="single">
        <el-form ref="formRef" :model="single" :rules="rules" label-width="108px" class="in-form">
          <div class="form-section-title">血液信息</div>
          <el-row :gutter="18">
            <el-col :span="8">
              <el-form-item label="血液品种" prop="product_name">
                <el-select v-model="single.product_name" placeholder="请选择品种" filterable @change="onSingleProductChange">
                  <el-option v-for="item in products" :key="item.id" :label="`${item.name}（${item.shelf_life_days}天）`" :value="item.name" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="ABO 血型">
                <el-radio-group v-model="single.blood_type">
                  <el-radio-button v-for="type in bloodTypes" :key="type" :value="type">{{ type }}</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="Rh 类型">
                <el-radio-group v-model="single.rh">
                  <el-radio-button v-for="rh in rhOptions" :key="rh" :value="rh">{{ rh === 'D阳性' ? 'Rh+' : 'Rh−' }}</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="18">
            <el-col :span="8">
              <el-form-item label="规格">
                <el-input v-model="single.specification" placeholder="如 2U / 200ml" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="数量">
                <el-input-number v-model="single.quantity" :min="0.5" :step="0.5" :precision="1" controls-position="right" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="包装">
                <el-input v-model="single.package" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="18">
            <el-col :span="8">
              <el-form-item label="采血日期" prop="collection_date">
                <el-date-picker v-model="single.collection_date" type="date" value-format="YYYY-MM-DD" placeholder="选择采血日期" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="自动有效期">
                <div class="readonly-value">{{ singleExpiry }}</div>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="自备血">
                <el-switch v-model="single.is_autologous" active-text="是" inactive-text="否" />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="form-section-title">来源与存放</div>
          <el-row :gutter="18">
            <el-col :span="8">
              <el-form-item label="来源血站">
                <el-input v-model="single.source" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="采血单位">
                <el-input v-model="single.collection_unit" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="献血者编号" prop="donor_no">
                <el-input v-model="single.donor_no" placeholder="如 D20240001" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="18">
            <el-col :span="12">
              <el-form-item label="存放冰箱" prop="fridge_id">
                <el-select v-model="single.fridge_id" placeholder="入库必须选择冰箱" style="width: 100%">
                  <el-option v-for="fridge in fridges" :key="fridge.id" :label="`${fridge.code} · ${fridge.name}（${fridge.location}）`" :value="fridge.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <div class="form-section-title">复检结果</div>
          <div class="retest-grid">
            <el-form-item v-for="item in retestLabels" :key="item.key" :label="item.label">
              <el-select v-model="single.retest_result[item.key]" style="width: 100%">
                <el-option v-for="option in retestOptions" :key="option" :label="option" :value="option" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-actions">
            <el-button @click="resetSingle">清空</el-button>
            <el-button type="primary" :loading="loading" @click="submitSingle">确认入库</el-button>
          </div>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="批量入库" name="batch">
        <div class="batch-common">
          <el-row :gutter="16">
            <el-col :span="6">
              <label>来源血站</label>
              <el-input v-model="batch.source" />
            </el-col>
            <el-col :span="6">
              <label>采血单位</label>
              <el-input v-model="batch.collection_unit" />
            </el-col>
            <el-col :span="6">
              <label>采血日期</label>
              <el-date-picker v-model="batch.collection_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-col>
            <el-col :span="6">
              <label>存放冰箱（必选）</label>
              <el-select v-model="batch.fridge_id" placeholder="选择冰箱" style="width: 100%">
                <el-option v-for="fridge in fridges" :key="fridge.id" :label="`${fridge.code} · ${fridge.name}`" :value="fridge.id" />
              </el-select>
            </el-col>
          </el-row>
          <div class="retest-inline">
            <span>统一复检结果</span>
            <el-select v-for="item in retestLabels" :key="item.key" v-model="batch.retest_result[item.key]" size="small" style="width: 86px">
              <el-option v-for="option in retestOptions" :key="option" :label="`${item.label} ${option}`" :value="option" />
            </el-select>
          </div>
        </div>

        <el-table :data="batch.items" border max-height="360">
          <el-table-column label="#" width="46" type="index" />
          <el-table-column label="品种" min-width="160">
            <template #default="{ row }">
              <el-select v-model="row.product_name" placeholder="选择品种" size="small" style="width: 100%">
                <el-option v-for="item in products" :key="item.id" :label="item.name" :value="item.name" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="血型" width="90">
            <template #default="{ row }">
              <el-select v-model="row.blood_type" size="small">
                <el-option v-for="type in bloodTypes" :key="type" :label="type" :value="type" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="Rh" width="100">
            <template #default="{ row }">
              <el-select v-model="row.rh" size="small">
                <el-option v-for="rh in rhOptions" :key="rh" :label="rh === 'D阳性' ? 'Rh+' : 'Rh−'" :value="rh" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="数量" width="105">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity" :min="0.5" :step="0.5" :precision="1" size="small" controls-position="right" style="width: 82px" />
            </template>
          </el-table-column>
          <el-table-column label="献血者编号" min-width="140">
            <template #default="{ row }"><el-input v-model="row.donor_no" size="small" /></template>
          </el-table-column>
          <el-table-column label="有效期" width="110">
            <template #default="{ row }"><span class="tabular">{{ rowExpiry(row) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="70">
            <template #default="{ $index }">
              <el-button text type="danger" :icon="Remove" @click="removeBatchRow($index)" />
            </template>
          </el-table-column>
        </el-table>
        <div class="batch-actions">
          <el-button :icon="Plus" @click="addBatchRow">添加一行</el-button>
          <el-button type="primary" :loading="loading" @click="submitBatch">批量提交入库</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.rule-strip {
  display: flex;
  gap: 32px;
  padding: 11px 16px;
  margin-bottom: 14px;
  color: var(--bb-text-secondary);
  font-size: 11px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
}

.rule-strip strong {
  margin-right: 5px;
  color: #1d4ed8;
}

.in-form {
  max-width: 1120px;
}

.form-section-title {
  padding: 6px 0 12px;
  margin: 8px 0 14px;
  color: var(--bb-text);
  font-size: 13px;
  font-weight: 700;
  border-bottom: 1px solid var(--bb-border);
}

.readonly-value {
  width: 100%;
  height: 32px;
  padding: 0 11px;
  color: #1d4ed8;
  font-weight: 700;
  line-height: 32px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
}

.retest-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0 18px;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 18px;
  margin-top: 8px;
  border-top: 1px solid var(--bb-border);
}

.batch-common {
  padding: 14px 16px;
  margin-bottom: 14px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 6px;
}

.batch-common label {
  display: block;
  margin-bottom: 6px;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.retest-inline {
  display: flex;
  gap: 8px;
  align-items: center;
  padding-top: 12px;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.batch-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 14px;
}
</style>
