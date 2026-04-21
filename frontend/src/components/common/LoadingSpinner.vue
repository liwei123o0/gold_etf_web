<script setup lang="ts">
defineProps<{
  size?: string
}>()
</script>

<template>
  <div class="spinner" :style="{ width: size || '16px', height: size || '16px' }">
    <div class="spinner-inner"></div>
  </div>
</template>

<style scoped lang="scss">
.spinner {
  display: inline-block;

  .spinner-inner {
    width: 100%;
    height: 100%;
    border: 2px solid rgba(0, 242, 255, 0.3);
    border-top-color: var(--accent-cyan);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
