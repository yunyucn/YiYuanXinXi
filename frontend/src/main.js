/** 前端入口：注册 Pinia、路由、全局业务组件和全局样式。 */

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import BloodBadge from '@/components/blood/BloodBadge.vue'
import CompatBanner from '@/components/blood/CompatBanner.vue'
import ExpiryBar from '@/components/blood/ExpiryBar.vue'
import RhTag from '@/components/blood/RhTag.vue'
import DecorPattern from '@/components/common/DecorPattern.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import RouteLoading from '@/components/common/RouteLoading.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import TableActions from '@/components/common/TableActions.vue'

import 'element-plus/theme-chalk/src/message.scss'
import 'element-plus/theme-chalk/src/message-box.scss'
import 'element-plus/theme-chalk/src/loading.scss'
import './styles/global.scss'
import './styles/interaction.scss'
import './styles/visual.scss'
import './styles/print.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

app.component('BloodBadge', BloodBadge)
app.component('RhTag', RhTag)
app.component('ExpiryBar', ExpiryBar)
app.component('CompatBanner', CompatBanner)
app.component('DecorPattern', DecorPattern)
app.component('PageHeader', PageHeader)
app.component('RouteLoading', RouteLoading)
app.component('StatusTag', StatusTag)
app.component('TableActions', TableActions)

app.mount('#app')
