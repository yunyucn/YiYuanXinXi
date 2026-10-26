<script setup>
import { Loading } from '@element-plus/icons-vue'
</script>

<template>
  <div class="route-loading page" role="status" aria-live="polite" aria-label="页面加载中">
    <div class="route-progress" />
    <div class="loading-hero">
      <span class="loading-icon"><el-icon :size="20" class="is-loading"><Loading /></el-icon></span>
      <div>
        <strong>页面加载中</strong>
        <span>正在初始化业务组件与数据视图</span>
      </div>
    </div>
    <div class="loading-grid">
      <i v-for="item in 4" :key="item" />
    </div>
    <div class="loading-card">
      <i class="line short" />
      <i class="line" />
      <i class="line medium" />
      <div class="loading-table">
        <span v-for="item in 6" :key="item" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.route-loading {
  position: relative;
  min-height: 520px;
  overflow: hidden;
}

.route-progress {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 2px;
  overflow: hidden;
  background: rgba(37, 99, 235, 0.1);
}

.route-progress::after {
  display: block;
  width: 38%;
  height: 100%;
  content: "";
  background: linear-gradient(90deg, transparent, #2563eb, #60a5fa, transparent);
  animation: route-progress 1.1s ease-in-out infinite;
}

.loading-hero,
.loading-grid,
.loading-card {
  background: var(--bb-card);
  border: 1px solid var(--bb-border);
  border-radius: 6px;
}

.loading-hero {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 18px;
  margin-bottom: 16px;
}

.loading-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  color: #2563eb;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #bfdbfe;
  border-radius: 6px;
}

.loading-hero strong,
.loading-hero span {
  display: block;
}

.loading-hero strong {
  font-size: 14px;
}

.loading-hero div > span {
  margin-top: 4px;
  color: var(--bb-text-secondary);
  font-size: 11px;
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  padding: 0;
  margin-bottom: 16px;
  background: transparent;
  border: 0;
}

.loading-grid i {
  height: 98px;
  background: linear-gradient(110deg, var(--bb-card) 20%, var(--bb-hover) 40%, var(--bb-card) 60%);
  background-size: 220% 100%;
  border: 1px solid var(--bb-border);
  border-radius: 6px;
  animation: shimmer 1.4s ease-in-out infinite;
}

.loading-card {
  padding: 20px;
}

.loading-card .line {
  display: block;
  width: 100%;
  height: 12px;
  margin-bottom: 12px;
  background: linear-gradient(110deg, var(--bb-hover) 20%, var(--bb-border) 40%, var(--bb-hover) 60%);
  background-size: 220% 100%;
  border-radius: 3px;
  animation: shimmer 1.4s ease-in-out infinite;
}

.loading-card .line.short {
  width: 28%;
  height: 18px;
}

.loading-card .line.medium {
  width: 62%;
}

.loading-table {
  display: grid;
  gap: 8px;
  margin-top: 22px;
}

.loading-table span {
  height: 34px;
  background: linear-gradient(110deg, var(--bb-hover) 20%, var(--bb-border) 40%, var(--bb-hover) 60%);
  background-size: 220% 100%;
  border-radius: 3px;
  animation: shimmer 1.4s ease-in-out infinite;
}

@keyframes shimmer {
  to {
    background-position: -120% 0;
  }
}

@keyframes route-progress {
  from {
    transform: translateX(-110%);
  }
  to {
    transform: translateX(300%);
  }
}
</style>
