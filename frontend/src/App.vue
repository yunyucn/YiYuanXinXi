<script setup>
/** 根组件：应用主题并注入 Element Plus 中文语言包。 */
import { onMounted } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useAppStore } from '@/store/app'

const appStore = useAppStore()

onMounted(() => {
  appStore.applyTheme()
})
</script>

<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>
