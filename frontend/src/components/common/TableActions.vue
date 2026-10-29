<script setup>
/**
 * 表格操作列组件。
 *
 * 将操作按钮收敛到同一行，超出 `max` 时自动折叠到“更多”菜单，
 * 避免不同页面因按钮数量导致布局错位。
 */
import { computed } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  max: { type: Number, default: 3 },
})

/** 过滤掉当前角色不可见的操作。 */
const available = computed(() => props.actions.filter((action) => !action.hidden))
/** 可在一行内直接展示的操作。 */
const inlineActions = computed(() => (available.value.length <= props.max ? available.value : available.value.slice(0, props.max - 1)))
/** 超出展示上限、收进下拉菜单的操作。 */
const overflowActions = computed(() => (available.value.length <= props.max ? [] : available.value.slice(props.max - 1)))

/** 执行操作前统一拦截禁用和加载中状态。 */
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
        :class="['table-action', `is-${action.type || 'primary'}`, { 'is-emphasis': action.emphasis }]"
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
  border-radius: 4px;
  transition: background 180ms ease-out, color 180ms ease-out, box-shadow 180ms ease-out, transform 180ms ease-out;
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

.table-actions :deep(.el-button.table-action:not(.is-emphasis):hover) {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(34, 211, 238, 0.09));
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.table-actions :deep(.el-button.table-action.is-danger:not(.is-emphasis):hover) {
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.11), rgba(251, 113, 133, 0.08));
  box-shadow: inset 0 0 0 1px rgba(220, 38, 38, 0.12);
}

.table-actions :deep(.el-button.table-action.is-emphasis) {
  position: relative;
  padding: 4px 9px;
  overflow: hidden;
  color: #fff;
  background: var(--bb-primary-gradient);
  border-radius: 4px;
  box-shadow: 0 4px 12px -8px rgba(37, 99, 235, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.table-actions :deep(.el-button.table-action.is-emphasis.is-warning) {
  background: var(--bb-warning-gradient);
  box-shadow: 0 4px 12px -8px rgba(217, 119, 6, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.table-actions :deep(.el-button.table-action.is-emphasis.is-success) {
  background: var(--bb-success-gradient);
  box-shadow: 0 4px 12px -8px rgba(5, 150, 105, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.table-actions :deep(.el-button.table-action.is-emphasis.is-danger) {
  background: var(--bb-danger-gradient);
  box-shadow: 0 4px 12px -8px rgba(220, 38, 38, 0.95), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.table-actions :deep(.el-button.table-action.is-emphasis::after) {
  position: absolute;
  inset: -20% -40%;
  content: "";
  background: linear-gradient(110deg, transparent 30%, rgba(255, 255, 255, 0.4) 48%, transparent 66%);
  transform: translateX(-130%) skewX(-10deg);
  transition: transform 520ms ease-out;
  pointer-events: none;
}

.table-actions :deep(.el-button.table-action.is-emphasis:hover) {
  color: #fff;
  filter: brightness(1.07) saturate(1.04);
  transform: translateY(-1px);
}

.table-actions :deep(.el-button.table-action.is-emphasis:hover::after) {
  transform: translateX(130%) skewX(-10deg);
}

.table-actions :deep(.el-button.table-action:hover .el-icon:not(.is-loading)) {
  transform: translateY(-1px) scale(1.07);
}

.table-actions :deep(.el-dropdown .el-button) {
  border-radius: 4px;
}

.table-actions :deep(.el-dropdown .el-button:hover) {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(34, 211, 238, 0.08));
}
</style>
