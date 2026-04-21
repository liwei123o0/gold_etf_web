<script setup lang="ts">
defineProps<{
  type?: 'button' | 'submit'
  loading?: boolean
  disabled?: boolean
}>()

defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    class="cyber-btn"
    :type="type || 'button'"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <span class="btn-text">
      <slot />
    </span>
    <span class="btn-loading">
      <slot name="loading">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </slot>
    </span>
  </button>
</template>

<style scoped lang="scss">
.cyber-btn {
  width: 100%;
  padding: 15px 24px;
  border: 1px solid rgba(0, 242, 255, 0.3);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(0, 242, 255, 0.15) 0%, rgba(102, 126, 234, 0.15) 100%);
  color: var(--accent-cyan);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(0, 242, 255, 0.15), transparent);
    transition: left 0.5s ease;
  }

  &:hover:not(:disabled)::before {
    left: 100%;
  }

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, rgba(0, 242, 255, 0.25) 0%, rgba(102, 126, 234, 0.25) 100%);
    border-color: rgba(0, 242, 255, 0.6);
    box-shadow: 0 0 30px rgba(0, 242, 255, 0.15), 0 10px 40px rgba(0, 0, 0, 0.3);
    transform: translateY(-1px);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  &:disabled::before {
    display: none;
  }

  .btn-text {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .btn-loading {
    display: none;
    align-items: center;
    gap: 8px;

    .dot {
      width: 6px;
      height: 6px;
      background: var(--accent-cyan);
      border-radius: 50%;
      animation: blink 1.4s infinite both;

      &:nth-child(2) {
        animation-delay: 0.2s;
      }

      &:nth-child(3) {
        animation-delay: 0.4s;
      }
    }
  }
}

.loading .btn-text {
  display: none;
}

.loading .btn-loading {
  display: flex;
}

@keyframes blink {
  0%, 80%, 100% {
    opacity: 0;
  }
  40% {
    opacity: 1;
  }
}
</style>
