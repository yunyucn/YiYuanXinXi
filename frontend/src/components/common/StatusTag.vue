<script setup>
import { computed } from 'vue'
import { statusType } from '@/utils/format'

const props = defineProps({
  status: { type: String, default: '' },
  type: { type: String, default: '' },
})

const tagType = computed(() => props.type || statusType(props.status))
</script>

<template>
  <el-tag :type="tagType" size="small" effect="light">{{ status }}</el-tag>
</template>
