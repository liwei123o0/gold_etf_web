<script setup lang="ts">
import { useAuth } from '@/composables/useAuth'
import { useClock } from '@/composables/useClock'

const { user, logout } = useAuth()
const { currentTime } = useClock()
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <span class="clock">{{ currentTime }}</span>
      <span class="header-title">股票技术分析系统</span>
    </div>
    <div class="header-right">
      <template v-if="user">
        <span class="user-info">{{ user.username }}</span>
        <span class="separator">|</span>
        <button class="logout-btn" @click="logout">退出</button>
      </template>
      <template v-else>
        <router-link to="/auth/login" class="header-link">登录</router-link>
        <span class="separator">|</span>
        <router-link to="/auth/register" class="header-link">注册</router-link>
      </template>
    </div>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(20px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.clock {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.user-info {
  color: var(--text-secondary);
}

.separator {
  color: var(--text-muted);
}

.header-link {
  color: var(--accent-purple);
  text-decoration: none;
  transition: color 0.2s;

  &:hover {
    color: var(--accent-cyan);
  }
}

.logout-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;

  &:hover {
    color: var(--accent-cyan);
    background: rgba(0, 242, 255, 0.1);
  }
}
</style>
