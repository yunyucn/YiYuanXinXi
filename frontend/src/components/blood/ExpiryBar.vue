<script setup>
import { computed } from 'vue'

const props = defineProps({
  expiryDate: { type: String, default: '' },
  days: { type: Number, default: null },
  status: { type: String, default: '' },
  level: { type: String, default: '' },
})

const dayCount = computed(() => {
  if (props.days !== null && props.days !== undefined) return Number(props.days)
  if (!props.expiryDate) return 0
  const target = new Date(`${props.expiryDate}T00:00:00`)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((target - today) / 86400000)
})

const level = computed(() => {
  if (props.level) return props.level
  if (props.status === '已过期' || dayCount.value <= 0) return 'expired'
  if (dayCount.value <= 3) return 'danger'
  if (dayCount.value <= 7) return 'warning'
  return 'ok'
})

const label = computed(() => {
  if (level.value === 'expired') return '已过期'
  return `${dayCount.value} 天`
})

const width = computed(() => {
  if (level.value === 'expired') return '100%'
  if (level.value === 'danger') return '30%'
  if (level.value === 'warning') return '60%'
  return '100%'
})
</script>

<template>
  <div class="expiry" :class="[level, { 'pulse-red': level === 'danger' }]">
    <span class="expiry-date">{{ expiryDate ? expiryDate.slice(0, 10) : '-' }}</span>
    <span class="bar"><i :style="{ width }" /></span>
    <span class="chip">{{ label }}</span>
  </div>
</template>

<style scoped>
.expiry {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.expiry-date {
  color: inherit;
  font-size: 12px;
}

.bar {
  width: 52px;
  height: 5px;
  overflow: hidden;
  background: #e2e8f0;
  border-radius: 4px;
}

.bar i {
  display: block;
  height: 100%;
  background: #059669;
  border-radius: 4px;
}

.chip {
  padding: 1px 6px;
  color: #065f46;
  font-size: 11px;
  background: #ecfdf5;
  border-radius: 4px;
}

.warning .bar i {
  background: #d97706;
}

.warning .chip {
  color: #92400e;
  background: #fffbeb;
}

.danger .bar i {
  background: #dc2626;
}

.danger .chip {
  color: #991b1b;
  background: #fef2f2;
}

.expired {
  color: #94a3b8;
  text-decoration: line-through;
}

.expired .bar i {
  background: #94a3b8;
}

.expired .chip {
  color: #64748b;
  text-decoration: none;
  background: #f1f5f9;
}
</style>
