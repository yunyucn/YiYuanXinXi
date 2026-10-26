import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '首页仪表盘' } },
      { path: 'in', name: 'blood-in', component: () => import('@/views/BloodBagIn.vue'), meta: { title: '血液入库', roles: ['tech'] } },
      { path: 'stock', name: 'stock', component: () => import('@/views/BloodBagStock.vue'), meta: { title: '库存管理', roles: ['tech', 'nurse', 'director'] } },
      { path: 'requests', name: 'requests', component: () => import('@/views/RequestList.vue'), meta: { title: '输血申请', roles: ['doctor', 'tech', 'director'] } },
      { path: 'cross-match', name: 'cross-match', component: () => import('@/views/CrossMatch.vue'), meta: { title: '配血工作台', roles: ['tech'] } },
      { path: 'issue', name: 'issue', component: () => import('@/views/Issue.vue'), meta: { title: '发血工作台', roles: ['tech'] } },
      { path: 'execute', name: 'execute', component: () => import('@/views/NurseExecute.vue'), meta: { title: '输血执行', roles: ['nurse'] } },
      { path: 'trace', name: 'trace', component: () => import('@/views/Trace.vue'), meta: { title: '全周期追溯' } },
      { path: 'alerts', name: 'alerts', component: () => import('@/views/AlertCenter.vue'), meta: { title: '预警中心', roles: ['tech', 'director'] } },
      { path: 'adverse', name: 'adverse', component: () => import('@/views/AdverseList.vue'), meta: { title: '不良反应', roles: ['nurse', 'tech', 'director'] } },
      { path: 'scrap', name: 'scrap', component: () => import('@/views/Scrap.vue'), meta: { title: '报废管理', roles: ['tech', 'director'] } },
      { path: 'report', name: 'report', component: () => import('@/views/Report.vue'), meta: { title: '统计报表', roles: ['director'] } },
      { path: 'system', name: 'system', component: () => import('@/views/system/SystemManage.vue'), meta: { title: '系统管理', roles: ['admin'] } },
    ],
  },
  {
    path: '/print/record/:id',
    name: 'print-record',
    component: () => import('@/views/print/TransfusionRecord.vue'),
    meta: { title: '输血记录单', blank: true },
  },
  {
    path: '/print/label/:id',
    name: 'print-label',
    component: () => import('@/views/print/BagLabel.vue'),
    meta: { title: '血袋标签', blank: true },
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.token && to.path === '/login') return '/dashboard'
    return true
  }
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      return '/login'
    }
  }
  if (to.meta.roles && !auth.hasRole(to.meta.roles)) {
    return '/dashboard'
  }
  return true
})

export default router
