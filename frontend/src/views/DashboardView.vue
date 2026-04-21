<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuth } from '@/composables/useAuth'

const { user, logout } = useAuth()

onMounted(() => {
  console.log('Dashboard loaded, user:', user.value)
})
</script>

<template>
  <div class="dashboard">
    <header class="header">
      <div class="header-left">
        <h1 class="title">黄金ETF技术分析系统</h1>
      </div>
      <div class="header-right">
        <span class="user-info">{{ user?.username }}</span>
        <button class="logout-btn" @click="logout">退出</button>
      </div>
    </header>
    <main class="main-content">
      <div class="welcome-card">
        <h2>欢迎回来, {{ user?.username }}!</h2>
        <p>主看板页面正在开发中...</p>
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  min-height: 100vh;
  background: var(--bg-primary);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(20px);
}

.title {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  color: var(--text-secondary);
  font-size: 14px;
}

.logout-btn {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
  }
}

.main-content {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.welcome-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 48px;
  text-align: center;

  h2 {
    color: var(--text-primary);
    margin-bottom: 16px;
  }

  p {
    color: var(--text-secondary);
  }
}
</style>
