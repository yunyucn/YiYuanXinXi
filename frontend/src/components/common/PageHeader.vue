<script setup>
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  min-height: 48px;
  margin-bottom: 18px;
}

h1 {
  margin: 0;
  color: var(--bb-text);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}

p {
  margin: 5px 0 0;
  color: var(--bb-text-secondary);
  font-size: 12px;
}

.page-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
  align-items: center;
}
</style>
