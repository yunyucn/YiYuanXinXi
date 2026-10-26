<script setup>
import { computed } from 'vue'

const props = defineProps({
  rh: { type: String, default: 'D阳性' },
})

const negative = computed(() => String(props.rh).includes('阴') || String(props.rh).endsWith('-'))
</script>

<template>
  <span class="rh-tag" :class="{ negative }">{{ negative ? 'Rh−' : 'Rh+' }}</span>
</template>

<style scoped>
.rh-tag {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 5px;
  color: #64748b;
  font-size: 10px;
  font-weight: 700;
  line-height: 18px;
  background: #f1f5f9;
  border-radius: 4px;
}

.rh-tag.negative {
  color: #dc2626;
  background: #fef2f2;
}
</style>
