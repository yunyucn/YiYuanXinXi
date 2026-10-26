<script setup>
import { computed } from 'vue'
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  level: { type: String, default: 'ok' },
  reason: { type: String, default: '' },
  title: { type: String, default: '' },
})

const heading = computed(() => props.title || ({ ok: '相容性校验通过', warn: '相容性提示', fail: '相容性校验不通过' }[props.level] || '相容性结果'))
</script>

<template>
  <div class="compat-banner" :class="level" role="status">
    <el-icon :size="18" class="compat-icon">
      <CircleCheckFilled v-if="level === 'ok'" />
      <WarningFilled v-else />
    </el-icon>
    <div>
      <strong>{{ heading }}</strong>
      <span v-if="reason">{{ reason }}</span>
    </div>
  </div>
</template>

<style scoped>
.compat-banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px 14px;
  color: #065f46;
  line-height: 1.5;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 6px;
}

.compat-banner strong {
  display: block;
  font-size: 13px;
}

.compat-icon {
  flex: 0 0 18px;
  margin-top: 1px;
}

.compat-banner span {
  display: block;
  margin-top: 2px;
  font-size: 12px;
}

.compat-banner.warn {
  color: #92400e;
  background: #fffbeb;
  border-color: #fde68a;
}

.compat-banner.fail {
  color: #991b1b;
  background: #fef2f2;
  border-color: #fecaca;
}
</style>
