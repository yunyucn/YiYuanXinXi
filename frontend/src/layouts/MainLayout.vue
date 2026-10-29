<script setup>
/**
 * 主布局：按角色生成菜单、展示首页预警角标并承载全局异常兜底。
 *
 * 菜单过滤只负责界面可见性，接口权限仍由后端 `roles_required` 强制执行。
 */
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Bell,
  Box,
  Connection,
  DataAnalysis,
  Document,
  Expand,
  FirstAidKit,
  Fold,
  HomeFilled,
  Moon,
  Setting,
  Sunny,
  Warning,
} from '@element-plus/icons-vue'
import { useAppStore } from '@/store/app'
import { useAuthStore } from '@/store/auth'
import { ACCESS } from '@/constants/access'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const appStore = useAppStore()
const bellRef = ref(null)
const routeError = ref(null)
let timer = null

/** 角色编码到中文名称的展示映射。 */
const roleNames = {
  admin: '血库管理员',
  tech: '输血科技师',
  doctor: '临床医生',
  nurse: '护士',
  director: '科室主任',
}

/** 主导航配置，子菜单通过权限矩阵过滤。 */
const menus = [
  { path: '/dashboard', label: '首页仪表盘', icon: HomeFilled },
  {
    label: '血液管理',
    icon: Box,
    children: [
      { path: '/in', label: '血液入库', icon: Document, roles: ACCESS.bloodIn },
      { path: '/stock', label: '库存管理', icon: Box, roles: ACCESS.stockView },
      { path: '/scrap', label: '报废管理', icon: Warning, roles: ACCESS.scrapView },
    ],
  },
  {
    label: '输血管理',
    icon: Connection,
    children: [
      { path: '/requests', label: '输血申请', icon: Document, roles: ACCESS.requestView },
      { path: '/cross-match', label: '配血工作台', icon: Connection, roles: ACCESS.crossMatch },
      { path: '/issue', label: '发血工作台', icon: FirstAidKit, roles: ACCESS.issue },
      { path: '/execute', label: '输血执行', icon: FirstAidKit, roles: ACCESS.execute },
      { path: '/trace', label: '全周期追溯', icon: Connection, roles: ACCESS.trace },
    ],
  },
  {
    label: '质控与统计',
    icon: DataAnalysis,
    children: [
      { path: '/alerts', label: '预警中心', icon: Warning, roles: ACCESS.alerts },
      { path: '/adverse', label: '不良反应', icon: Warning, roles: ACCESS.adverse },
      { path: '/report', label: '统计报表', icon: DataAnalysis, roles: ACCESS.report },
    ],
  },
  { path: '/system', label: '系统管理', icon: Setting, roles: ACCESS.system },
]

/** 过滤无权限菜单并移除空分组。 */
const visibleMenus = computed(() =>
  menus
    .map((menu) => {
      if (menu.children) {
        return { ...menu, children: menu.children.filter((item) => auth.hasRole(item.roles)) }
      }
      return menu
    })
    .filter((menu) => (menu.children ? menu.children.length > 0 : auth.hasRole(menu.roles))),
)

/** 当前页面标题。 */
const currentTitle = computed(() => route.meta.title || '输血管理分系统')
/** 顶栏用户头像文字。 */
const userInitial = computed(() => auth.user?.real_name?.slice(0, 1) || '血')
/** 当前角色是否可见预警入口。 */
const canViewAlerts = computed(() => auth.canAccess('alerts'))

/** 将预警级别映射为下拉项样式。 */
function levelClass(level) {
  return { 严重: 'danger', 警告: 'warning', 提示: 'info' }[level] || 'info'
}

/** 处理用户菜单中的退出登录与追溯跳转。 */
async function handleCommand(command) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确认退出当前账号吗？', '退出登录', { type: 'warning' })
    appStore.clearAlertSummary()
    await auth.logout()
    router.replace('/login')
  } else if (command === 'trace') {
    router.push('/trace')
  }
}

/** 具有预警权限时跳转预警中心。 */
function goAlert() {
  if (!canViewAlerts.value) return
  bellRef.value?.hide?.()
  router.push('/alerts')
}

// 捕获子页面渲染异常，展示可恢复的错误提示，避免整页白屏。
onErrorCaptured((error) => {
  routeError.value = error
  console.error('[route-error]', error)
  return false
})

/** 清除路由错误并重新加载当前页面。 */
function retryRoute() {
  routeError.value = null
  window.location.reload()
}

// 有权限时每分钟刷新预警角标；无权限时主动清空残留状态。
onMounted(() => {
  if (canViewAlerts.value) {
    appStore.fetchAlertSummary()
    timer = window.setInterval(() => appStore.fetchAlertSummary(), 60000)
  } else {
    appStore.clearAlertSummary()
  }
})

// 离开布局时释放轮询定时器。
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand" :class="{ collapsed: appStore.collapsed }">
        <span class="brand-mark" aria-hidden="true">
          <el-icon :size="17"><FirstAidKit /></el-icon>
        </span>
        <div v-show="!appStore.collapsed" class="brand-copy">
          <strong>输血管理分系统</strong>
          <span>BLOOD BANK · 临床用血闭环</span>
        </div>
      </div>

      <div class="header-main">
        <button class="icon-button focusable" type="button" :aria-label="appStore.collapsed ? '展开侧边栏' : '折叠侧边栏'" @click="appStore.toggleSidebar">
          <el-icon :size="19"><Expand v-if="appStore.collapsed" /><Fold v-else /></el-icon>
        </button>
        <div class="breadcrumb">
          <span>输血管理</span>
          <i>/</i>
          <strong>{{ currentTitle }}</strong>
        </div>
        <div class="header-actions">
          <el-popover v-if="canViewAlerts" ref="bellRef" placement="bottom-end" :width="360" trigger="click">
            <template #reference>
              <button class="icon-button bell-button focusable" type="button" aria-label="预警通知" @click="appStore.fetchAlertSummary()">
                <el-icon :size="20" :class="{ 'bell-swing': appStore.bellBounce }"><Bell /></el-icon>
                <span v-if="appStore.alertCount" class="bell-count" :class="{ 'bell-bounce': appStore.bellBounce }">
                  {{ appStore.alertCount > 99 ? '99+' : appStore.alertCount }}
                </span>
              </button>
            </template>
            <div class="alert-popover">
              <div class="popover-title">
                <strong>未处理预警</strong>
                <span>仅统计警告与严重</span>
              </div>
              <div v-if="appStore.latestAlerts.length" class="popover-list">
                <div v-for="item in appStore.latestAlerts" :key="item.id" class="popover-item">
                  <i :class="levelClass(item.level)" />
                  <div>
                    <strong>{{ item.type }} · {{ item.level }}</strong>
                    <p>{{ item.content }}</p>
                  </div>
                </div>
              </div>
              <div v-else class="popover-empty">暂无未处理预警</div>
              <button class="popover-more" type="button" @click="goAlert">查看全部预警</button>
            </div>
          </el-popover>

          <button class="icon-button focusable" type="button" :aria-label="appStore.dark ? '切换浅色模式' : '切换暗色模式'" @click="appStore.toggleTheme()">
            <el-icon :size="19"><Sunny v-if="appStore.dark" /><Moon v-else /></el-icon>
          </button>

          <el-dropdown trigger="click" @command="handleCommand">
            <button class="user-trigger focusable" type="button">
              <span class="avatar">{{ userInitial }}</span>
              <span class="user-copy">
                <strong>{{ auth.user?.real_name || '未登录' }}</strong>
                <small>{{ roleNames[auth.role] || auth.user?.role_name }}</small>
              </span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="auth.canAccess('trace')" command="trace">全周期追溯</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <div class="app-body">
      <aside class="sidebar" :class="{ collapsed: appStore.collapsed }">
        <el-menu :default-active="route.path" :collapse="appStore.collapsed" router class="side-menu">
          <template v-for="menu in visibleMenus" :key="menu.label || menu.path">
            <el-sub-menu v-if="menu.children" :index="menu.label">
              <template #title>
                <el-icon><component :is="menu.icon" /></el-icon>
                <span>{{ menu.label }}</span>
              </template>
              <el-menu-item v-for="child in menu.children" :key="child.path" :index="child.path">
                <el-icon><component :is="child.icon" /></el-icon>
                <span>{{ child.label }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="menu.path">
              <el-icon><component :is="menu.icon" /></el-icon>
              <span>{{ menu.label }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </aside>

      <main class="main-content">
        <div v-if="routeError" class="route-error">
          <el-icon :size="34"><Warning /></el-icon>
          <h2>页面加载失败</h2>
          <p>当前业务页初始化时发生异常，系统已阻止整页白屏。</p>
          <el-button type="primary" @click="retryRoute">重新加载</el-button>
        </div>
        <router-view v-else v-slot="{ Component }">
          <Suspense :timeout="0" @resolve="routeError = null">
            <component :is="Component" :key="route.path" />
            <template #fallback>
              <RouteLoading />
            </template>
          </Suspense>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--bb-bg);
}

.app-header {
  display: flex;
  flex: 0 0 64px;
  height: 64px;
  background: var(--bb-header);
  border-bottom: 1px solid var(--bb-border);
}

.brand {
  display: flex;
  flex: 0 0 220px;
  gap: 10px;
  align-items: center;
  width: 220px;
  padding: 0 18px;
  overflow: hidden;
  border-right: 1px solid var(--bb-border);
  transition: width 150ms ease-out, flex-basis 150ms ease-out, padding 150ms ease-out;
}

.brand.collapsed {
  flex-basis: 64px;
  width: 64px;
  justify-content: center;
  padding: 0;
}

.brand-mark {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: #fff;
  background: linear-gradient(135deg, #1e40af, #2563eb 58%, #3b82f6);
  border-radius: 9px;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.32);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-copy strong {
  color: var(--bb-text);
  font-size: 15px;
  white-space: nowrap;
}

.brand-copy span {
  margin-top: 2px;
  color: var(--bb-text-secondary);
  font-size: 9px;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.header-main {
  display: flex;
  flex: 1;
  gap: 16px;
  align-items: center;
  min-width: 0;
  padding: 0 20px;
}

.icon-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  padding: 0;
  color: var(--bb-text-secondary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
}

.icon-button:hover {
  color: var(--bb-primary);
  background: var(--bb-hover);
  border-color: var(--bb-border);
}

.breadcrumb {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.breadcrumb i {
  color: #cbd5e1;
  font-style: normal;
}

.breadcrumb strong {
  color: var(--bb-text);
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

.bell-count {
  position: absolute;
  top: -2px;
  right: -3px;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  line-height: 17px;
  text-align: center;
  background: #dc2626;
  border: 2px solid var(--bb-header);
  border-radius: 10px;
}

.user-trigger {
  display: flex;
  gap: 9px;
  align-items: center;
  padding: 4px 6px;
  color: var(--bb-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
}

.user-trigger:hover {
  background: var(--bb-hover);
  border-color: var(--bb-border);
}

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  background: #2563eb;
  border-radius: 50%;
}

.user-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.user-copy strong {
  font-size: 12px;
  line-height: 1.4;
}

.user-copy small {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.app-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.sidebar {
  display: flex;
  flex: 0 0 220px;
  flex-direction: column;
  width: 220px;
  overflow: hidden;
  background: var(--bb-sidebar);
  border-right: 1px solid var(--bb-border);
  transition: width 150ms ease-out, flex-basis 150ms ease-out;
}

.sidebar.collapsed {
  flex-basis: 64px;
  width: 64px;
}

.side-menu {
  flex: 1;
  padding: 10px 8px;
  overflow-y: auto;
  border-right: 0;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--bb-text-secondary);
  --el-menu-hover-bg-color: var(--bb-hover);
  --el-menu-active-color: var(--bb-primary);
  --el-menu-item-height: 48px;
  --el-menu-sub-item-height: 44px;
}

.main-content {
  flex: 1;
  min-width: 1024px;
  padding: 20px;
  overflow: auto;
  background: var(--bb-bg);
}

.route-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 420px;
  padding: 40px;
  color: var(--bb-text-secondary);
  text-align: center;
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 8px;
}

.route-error .el-icon {
  color: var(--bb-warning);
}

.route-error h2 {
  margin: 16px 0 6px;
  color: var(--bb-text);
  font-size: 18px;
}

.route-error p {
  margin: 0 0 20px;
  font-size: 13px;
}

.alert-popover {
  padding: 2px;
}

.popover-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 4px 4px 10px;
  border-bottom: 1px solid var(--bb-border);
}

.popover-title strong {
  color: var(--bb-text);
  font-size: 13px;
}

.popover-title span {
  color: var(--bb-text-secondary);
  font-size: 10px;
}

.popover-list {
  max-height: 300px;
  overflow-y: auto;
}

.popover-item {
  display: flex;
  gap: 9px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--bb-border);
}

.popover-item i {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  margin-top: 5px;
  background: #2563eb;
  border-radius: 50%;
}

.popover-item i.warning {
  background: #d97706;
}

.popover-item i.danger {
  background: #dc2626;
}

.popover-item strong {
  color: var(--bb-text);
  font-size: 11px;
}

.popover-item p {
  margin: 3px 0 0;
  color: var(--bb-text-secondary);
  font-size: 11px;
  line-height: 1.5;
}

.popover-empty {
  padding: 28px 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
  text-align: center;
}

.popover-more {
  width: 100%;
  padding: 9px 0 3px;
  color: var(--bb-primary);
  font-size: 12px;
  background: transparent;
  border: 0;
  cursor: pointer;
}
</style>
