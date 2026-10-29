<script setup>
/**
 * 系统管理：用户、科室、品种、冰箱字典及操作日志。
 *
 * 页面仅管理员可进入；用户启停、密码重置和基础数据写操作均会写入后端审计日志。
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Plus, Refresh, Search } from '@element-plus/icons-vue'
import { systemApi } from '@/api'
import { formatDateTime } from '@/utils/format'

const activeTab = ref('users')
const loading = ref(false)
const users = ref([])
const departments = ref([])
const roles = ref([])
const products = ref([])
const fridges = ref([])
const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(20)
const logKeyword = ref('')

const userVisible = ref(false)
const userSaving = ref(false)
const userForm = reactive({
  id: null,
  username: '',
  real_name: '',
  role_code: 'doctor',
  department_id: null,
  title: '',
  phone: '',
  password: '',
})

const deptVisible = ref(false)
const deptSaving = ref(false)
const deptForm = reactive({ code: '', name: '', phone: '' })

const productVisible = ref(false)
const productSaving = ref(false)
const productForm = reactive({ id: null, name: '', category: '红细胞', shelf_life_days: 35, safe_stock: 4, unit: 'U', description: '' })

const fridgeVisible = ref(false)
const fridgeSaving = ref(false)
const fridgeForm = reactive({ id: null, code: '', name: '', location: '', capacity: 30, status: '正常' })

/** 用户表单是否处于编辑模式。 */
const isEditingUser = computed(() => Boolean(userForm.id))
/** 品种表单是否处于编辑模式。 */
const isEditingProduct = computed(() => Boolean(productForm.id))
/** 冰箱表单是否处于编辑模式。 */
const isEditingFridge = computed(() => Boolean(fridgeForm.id))
const categories = ['全血', '红细胞', '血浆', '血小板', '冷沉淀']
const units = ['U', 'ml']

/** 角色编码到标签颜色的映射。 */
function roleTag(role) {
  return { admin: 'danger', tech: 'primary', doctor: 'success', nurse: 'warning', director: 'info' }[role] || 'info'
}

/** 并行加载用户、科室、角色、品种和冰箱基础数据。 */
async function loadBase() {
  loading.value = true
  try {
    const [userList, departmentList, roleList, productList, fridgeList] = await Promise.all([
      systemApi.users(),
      systemApi.departments(),
      systemApi.roles(),
      systemApi.products(),
      systemApi.fridges(),
    ])
    users.value = userList
    departments.value = departmentList
    roles.value = roleList
    products.value = productList
    fridges.value = fridgeList
  } finally {
    loading.value = false
  }
}

/** 按关键字分页加载操作审计日志。 */
async function loadLogs() {
  const data = await systemApi.logs({ keyword: logKeyword.value || undefined, page: logPage.value, page_size: logPageSize.value })
  logs.value = data.items
  logTotal.value = data.total
}

/** 根据当前页签刷新对应数据。 */
async function refreshCurrent() {
  if (activeTab.value === 'logs') await loadLogs()
  else await loadBase()
}

/** 打开新增或编辑用户弹窗。 */
function openUser(row = null) {
  Object.assign(userForm, {
    id: row?.id || null,
    username: row?.username || '',
    real_name: row?.real_name || '',
    role_code: row?.role || 'doctor',
    department_id: row?.department_id || departments.value[0]?.id || null,
    title: row?.title || '',
    phone: row?.phone || '',
    password: '',
  })
  userVisible.value = true
}

/** 保存用户资料；编辑时密码留空表示不修改。 */
async function saveUser() {
  if (!userForm.username.trim() || !userForm.real_name.trim() || !userForm.role_code) {
    ElMessage.warning('用户名、姓名和角色为必填项')
    return
  }
  userSaving.value = true
  try {
    if (isEditingUser.value) {
      const payload = {
        real_name: userForm.real_name.trim(),
        department_id: userForm.department_id || null,
        title: userForm.title,
        phone: userForm.phone,
      }
      if (userForm.password) payload.password = userForm.password
      await systemApi.updateUser(userForm.id, payload)
      ElMessage.success('用户信息已更新')
    } else {
      await systemApi.createUser({
        username: userForm.username.trim(),
        real_name: userForm.real_name.trim(),
        role_code: userForm.role_code,
        department_id: userForm.department_id || null,
        title: userForm.title,
        phone: userForm.phone,
        password: userForm.password || '123456',
      })
      ElMessage.success('用户已创建')
    }
    userVisible.value = false
    await loadBase()
  } finally {
    userSaving.value = false
  }
}

/** 启用或停用账号，失败时回滚开关状态。 */
async function toggleUser(row, value) {
  try {
    await systemApi.updateUser(row.id, { is_active: value })
    ElMessage.success(value ? '用户已启用' : '用户已停用')
  } catch {
    row.is_active = !value
  }
}

/** 打开新增科室弹窗。 */
function openDepartment() {
  Object.assign(deptForm, { code: '', name: '', phone: '' })
  deptVisible.value = true
}

/** 校验并创建科室。 */
async function saveDepartment() {
  if (!deptForm.code.trim() || !deptForm.name.trim()) {
    ElMessage.warning('科室编码和名称为必填项')
    return
  }
  deptSaving.value = true
  try {
    await systemApi.createDepartment({ code: deptForm.code.trim(), name: deptForm.name.trim(), phone: deptForm.phone })
    ElMessage.success('科室已创建')
    deptVisible.value = false
    await loadBase()
  } finally {
    deptSaving.value = false
  }
}

/** 打开新增或编辑血液品种弹窗。 */
function openProduct(row = null) {
  Object.assign(productForm, {
    id: row?.id || null,
    name: row?.name || '',
    category: row?.category || '红细胞',
    shelf_life_days: row?.shelf_life_days || 35,
    safe_stock: row?.safe_stock || 0,
    unit: row?.unit || 'U',
    description: row?.description || '',
  })
  productVisible.value = true
}

/** 保存品种字典配置。 */
async function saveProduct() {
  if (!productForm.name.trim()) {
    ElMessage.warning('品种名称为必填项')
    return
  }
  if (Number(productForm.shelf_life_days) <= 0) {
    ElMessage.warning('保质期必须大于 0 天')
    return
  }
  productSaving.value = true
  try {
    if (isEditingProduct.value) {
      await systemApi.updateProduct(productForm.id, {
        category: productForm.category,
        shelf_life_days: Number(productForm.shelf_life_days),
        safe_stock: Number(productForm.safe_stock),
        unit: productForm.unit,
        description: productForm.description,
      })
      ElMessage.success('品种字典已更新')
    } else {
      await systemApi.createProduct({
        name: productForm.name.trim(),
        category: productForm.category,
        shelf_life_days: Number(productForm.shelf_life_days),
        safe_stock: Number(productForm.safe_stock),
        unit: productForm.unit,
        description: productForm.description,
      })
      ElMessage.success('品种已创建')
    }
    productVisible.value = false
    await loadBase()
  } finally {
    productSaving.value = false
  }
}

/** 打开新增或编辑储血设备弹窗。 */
function openFridge(row = null) {
  Object.assign(fridgeForm, {
    id: row?.id || null,
    code: row?.code || '',
    name: row?.name || '',
    location: row?.location || '',
    capacity: row?.capacity || 30,
    status: row?.status || '正常',
  })
  fridgeVisible.value = true
}

/** 保存储血设备信息与运行状态。 */
async function saveFridge() {
  if (!fridgeForm.code.trim() || !fridgeForm.name.trim() || !fridgeForm.location.trim()) {
    ElMessage.warning('冰箱编号、名称和位置为必填项')
    return
  }
  fridgeSaving.value = true
  try {
    if (isEditingFridge.value) {
      await systemApi.updateFridge(fridgeForm.id, {
        name: fridgeForm.name.trim(),
        location: fridgeForm.location.trim(),
        capacity: Number(fridgeForm.capacity),
        status: fridgeForm.status,
      })
      ElMessage.success('冰箱信息已更新')
    } else {
      await systemApi.createFridge({
        code: fridgeForm.code.trim(),
        name: fridgeForm.name.trim(),
        location: fridgeForm.location.trim(),
        capacity: Number(fridgeForm.capacity),
        status: fridgeForm.status,
      })
      ElMessage.success('冰箱已创建')
    }
    fridgeVisible.value = false
    await loadBase()
  } finally {
    fridgeSaving.value = false
  }
}

/** 搜索审计日志并回到第一页。 */
function searchLogs() {
  logPage.value = 1
  loadLogs()
}

// 首次进入日志页签时按需加载审计日志。
watch(activeTab, (value) => {
  if (value === 'logs' && !logs.value.length) loadLogs()
})

onMounted(async () => {
  await loadBase()
  await loadLogs()
})
</script>

<template>
  <div class="page">
    <PageHeader title="系统管理" description="维护用户角色、临床科室、血液品种字典、储血冰箱与系统操作日志">
      <template #actions>
        <el-button :icon="Refresh" :loading="loading" @click="refreshCurrent">刷新</el-button>
      </template>
    </PageHeader>

    <section class="page-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="用户管理" name="users">
          <div class="tab-toolbar">
            <span>系统账号与角色权限，管理员可停用账号或重置密码。</span>
            <el-button type="primary" :icon="Plus" @click="openUser()">新增用户</el-button>
          </div>
          <el-table v-loading="loading" :data="users" border>
            <el-table-column prop="username" label="用户名" width="110" />
            <el-table-column prop="real_name" label="姓名" width="100" />
            <el-table-column label="角色" width="120">
              <template #default="{ row }"><el-tag :type="roleTag(row.role)" size="small">{{ row.role_name }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="department" label="科室" min-width="120" />
            <el-table-column prop="title" label="职称" min-width="110" />
            <el-table-column prop="phone" label="联系电话" width="130" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.is_active" size="small" inline-prompt active-text="启用" inactive-text="停用" @change="(value) => toggleUser(row, value)" />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="158">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="96" fixed="right" align="center">
              <template #default="{ row }">
                <TableActions :actions="[{ label: '编辑', icon: Edit, onClick: () => openUser(row) }]" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="科室管理" name="departments">
          <div class="tab-toolbar">
            <span>输血申请与报表按科室聚合。</span>
            <el-button type="primary" :icon="Plus" @click="openDepartment">新增科室</el-button>
          </div>
          <el-table v-loading="loading" :data="departments" border>
            <el-table-column prop="code" label="科室编码" width="140" />
            <el-table-column prop="name" label="科室名称" min-width="180" />
            <el-table-column prop="phone" label="联系电话" width="180" />
            <el-table-column label="关联用户" width="110" align="right">
              <template #default="{ row }">{{ users.filter((user) => user.department_id === row.id).length }} 人</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="品种字典" name="products">
          <div class="tab-toolbar">
            <span>保质期用于入库时自动计算有效期，安全库存用于低库存预警。</span>
            <el-button type="primary" :icon="Plus" @click="openProduct()">新增品种</el-button>
          </div>
          <el-table v-loading="loading" :data="products" border>
            <el-table-column prop="name" label="品种名称" min-width="140" />
            <el-table-column prop="category" label="分类" width="110" />
            <el-table-column prop="shelf_life_days" label="保质期（天）" width="120" align="right" />
            <el-table-column label="安全库存" width="120" align="right">
              <template #default="{ row }">{{ row.safe_stock }}{{ row.unit }}</template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
            <el-table-column label="操作" width="96" fixed="right" align="center">
              <template #default="{ row }">
                <TableActions :actions="[{ label: '编辑', icon: Edit, onClick: () => openProduct(row) }]" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="冰箱管理" name="fridges">
          <div class="tab-toolbar">
            <span>入库时必须选择正常状态的储血冰箱，冰箱视图按容量展示血袋分布。</span>
            <el-button type="primary" :icon="Plus" @click="openFridge()">新增冰箱</el-button>
          </div>
          <el-table v-loading="loading" :data="fridges" border>
            <el-table-column prop="code" label="冰箱编号" width="120" />
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column prop="location" label="位置" min-width="180" />
            <el-table-column prop="capacity" label="容量（袋）" width="120" align="right" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><el-tag :type="row.status === '正常' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="96" fixed="right" align="center">
              <template #default="{ row }">
                <TableActions :actions="[{ label: '编辑', icon: Edit, onClick: () => openFridge(row) }]" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="操作日志" name="logs">
          <div class="filter-bar">
            <el-input v-model="logKeyword" :prefix-icon="Search" clearable placeholder="用户名 / 操作 / 详情" style="width: 280px" @keyup.enter="searchLogs" />
            <el-button type="primary" :icon="Search" @click="searchLogs">查询</el-button>
            <el-button @click="logKeyword = ''; searchLogs()">重置</el-button>
          </div>
          <el-table :data="logs" border>
            <el-table-column prop="created_at" label="操作时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="username" label="操作人" width="110" />
            <el-table-column prop="action" label="操作" width="150" />
            <el-table-column prop="target_type" label="对象类型" width="110" />
            <el-table-column prop="target_id" label="对象标识" width="150" show-overflow-tooltip />
            <el-table-column prop="detail" label="操作详情" min-width="300" show-overflow-tooltip />
          </el-table>
          <div class="table-footer">
            <el-pagination v-model:current-page="logPage" v-model:page-size="logPageSize" :total="logTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadLogs" @size-change="loadLogs" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="userVisible" :title="isEditingUser ? '编辑用户' : '新增用户'" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="用户名"><el-input v-model="userForm.username" :disabled="isEditingUser" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="姓名"><el-input v-model="userForm.real_name" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="角色">
              <el-select v-model="userForm.role_code" :disabled="isEditingUser" style="width: 100%">
                <el-option v-for="item in roles" :key="item.code" :label="item.name" :value="item.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="科室">
              <el-select v-model="userForm.department_id" clearable style="width: 100%">
                <el-option v-for="item in departments" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="职称"><el-input v-model="userForm.title" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话"><el-input v-model="userForm.phone" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item :label="isEditingUser ? '重置密码（留空不修改）' : '初始密码'"><el-input v-model="userForm.password" type="password" show-password placeholder="默认 123456" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="userVisible = false">取消</el-button><el-button type="primary" :loading="userSaving" @click="saveUser">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="deptVisible" title="新增科室" width="460px">
      <el-form label-position="top">
        <el-form-item label="科室编码"><el-input v-model="deptForm.code" placeholder="如 DEPT10" /></el-form-item>
        <el-form-item label="科室名称"><el-input v-model="deptForm.name" placeholder="如 血液内科" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="deptForm.phone" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="deptVisible = false">取消</el-button><el-button type="primary" :loading="deptSaving" @click="saveDepartment">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="productVisible" :title="isEditingProduct ? '编辑品种' : '新增品种'" width="560px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="品种名称"><el-input v-model="productForm.name" :disabled="isEditingProduct" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="分类"><el-select v-model="productForm.category" style="width: 100%"><el-option v-for="item in categories" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="保质期（天）"><el-input-number v-model="productForm.shelf_life_days" :min="1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="安全库存"><el-input-number v-model="productForm.safe_stock" :min="0" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="单位"><el-select v-model="productForm.unit" style="width: 100%"><el-option v-for="item in units" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
        </el-row>
        <el-form-item label="说明"><el-input v-model="productForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="productVisible = false">取消</el-button><el-button type="primary" :loading="productSaving" @click="saveProduct">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="fridgeVisible" :title="isEditingFridge ? '编辑冰箱' : '新增冰箱'" width="520px">
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="冰箱编号"><el-input v-model="fridgeForm.code" :disabled="isEditingFridge" placeholder="如 F05" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="名称"><el-input v-model="fridgeForm.name" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="位置"><el-input v-model="fridgeForm.location" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="容量（袋）"><el-input-number v-model="fridgeForm.capacity" :min="1" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态"><el-select v-model="fridgeForm.status" style="width: 100%"><el-option label="正常" value="正常" /><el-option label="维护" value="维护" /></el-select></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer><el-button @click="fridgeVisible = false">取消</el-button><el-button type="primary" :loading="fridgeSaving" @click="saveFridge">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 14px;
  color: var(--bb-text-secondary);
  font-size: 11px;
  background: var(--bb-hover);
  border: 1px solid var(--bb-border);
  border-radius: 4px;
}
</style>
