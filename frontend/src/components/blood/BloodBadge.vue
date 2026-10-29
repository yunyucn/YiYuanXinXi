<script setup>
/** 血型圆形标识，按 ABO 类型使用固定系统色。 */
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: '' },
  size: { type: Number, default: 28 },
})

/** ABO 血型对应的标识色。 */
const colors = {
  A: '#2563EB',
  B: '#D97706',
  AB: '#7C3AED',
  O: '#059669',
}

/** 根据尺寸和血型生成标识样式。 */
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  background: colors[props.type] || '#64748B',
  fontSize: `${Math.max(10, props.size * 0.38)}px`,
}))
</script>

<template>
  <span class="blood-badge" :style="style" :title="`${type} 型`">{{ type || '?' }}</span>
</template>

<style scoped>
.blood-badge {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  line-height: 1;
  border-radius: 50%;
  user-select: none;
}
</style>
