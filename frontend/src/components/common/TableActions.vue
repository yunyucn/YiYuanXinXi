<script setup>
import { computed } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  max: { type: Number, default: 3 },
})

const available = computed(() => props.actions.filter((action) => !action.hidden))
const inlineActions = computed(() => (available.value.length <= props.max ? available.value : available.value.slice(0, props.max - 1)))
const overflowActions = computed(() => (available.value.length <= props.max ? [] : available.value.slice(props.max - 1)))

function run(action) {
  if (action.disabled || action.loading) return
  action.onClick?.()
}
</script>

<template>
  <div class="table-actions" @click.stop>
    <el-tooltip
      v-for="action in inlineActions"
      :key="action.label"
      :content="action.tooltip || action.label"
      :disabled="!action.tooltip"
      placement="top"
      :show-after="180"
    >
      <el-button
        link
        :type="action.type || 'primary'"
        :icon="action.icon"
        :loading="action.loading"
        :disabled="action.disabled"
        @click="run(action)"
      >
        <span v-if="!action.iconOnly">{{ action.label }}</span>
      </el-button>
    </el-tooltip>

    <el-dropdown v-if="overflowActions.length" trigger="click" placement="bottom-end">
      <el-button link type="info" :icon="MoreFilled" aria-label="更多操作" />
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="action in overflowActions"
            :key="action.label"
            :disabled="action.disabled"
            @click="run(action)"
          >
            {{ action.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<style scoped>
.table-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: 2px;
  align-items: center;
  justify-content: center;
  min-width: max-content;
  white-space: nowrap;
}

.table-actions :deep(.el-button) {
  height: 26px;
  padding: 3px 5px;
  margin-left: 0;
  font-size: 12px;
  line-height: 1;
  flex: 0 0 auto;
}

.table-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.table-actions :deep(.el-icon) {
  font-size: 14px;
  vertical-align: middle;
}

.table-actions :deep(.el-button > span) {
  gap: 3px;
  align-items: center;
  line-height: 1;
}
</style>
