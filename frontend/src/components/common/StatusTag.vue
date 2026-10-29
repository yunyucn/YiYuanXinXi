<script setup>
/** 业务状态标签，复用全局状态到颜色的映射。 */
import { computed } from 'vue'
import { statusType } from '@/utils/format'

const props = defineProps({
  status: { type: String, default: '' },
  type: { type: String, default: '' },
})

/** 优先使用显式类型，否则按状态推导标签颜色。 */
const tagType = computed(() => props.type || statusType(props.status))
</script>

<template>
  <el-tag :type="tagType" size="small" effect="light">{{ status }}</el-tag>
</template>
