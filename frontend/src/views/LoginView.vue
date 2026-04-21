<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuth } from '@/composables/useAuth'
import CyberButton from '@/components/common/CyberButton.vue'

const { login, loading } = useAuth()

const username = ref('')
const password = ref('')
const errorMsg = ref('')
const showPassword = ref(false)

let canvas: HTMLCanvasElement | null = null
let ctx: CanvasRenderingContext2D | null = null
let animationId: number | null = null
let particles: Particle[] = []

class Particle {
  x = 0
  y = 0
  size = 0
  speedX = 0
  speedY = 0
  opacity = 0
  color = ''

  constructor(W: number, H: number) {
    this.reset(W, H)
  }

  reset(W: number, H: number) {
    this.x = Math.random() * W
    this.y = Math.random() * H
    this.size = Math.random() * 1.5 + 0.5
    this.speedX = (Math.random() - 0.5) * 0.4
    this.speedY = (Math.random() - 0.5) * 0.4
    this.opacity = Math.random() * 0.5 + 0.1
    this.color = Math.random() > 0.5 ? '0,242,255' : '102,126,234'
  }

  update(W: number, H: number) {
    this.x += this.speedX
    this.y += this.speedY
    if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) {
      this.reset(W, H)
    }
  }

  draw() {
    if (!ctx) return
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${this.color},${this.opacity})`
    ctx.fill()
  }
}

function drawLines(W: number, H: number) {
  if (!ctx) return
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 120) {
        const opacity = (1 - dist / 120) * 0.15
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `rgba(102,126,234,${opacity})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }
}

function animate() {
  if (!canvas || !ctx) return
  const W = canvas.width
  const H = canvas.height
  ctx.clearRect(0, 0, W, H)
  particles.forEach(p => {
    p.update(W, H)
    p.draw()
  })
  drawLines(W, H)
  animationId = requestAnimationFrame(animate)
}

function resize() {
  if (!canvas) return
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
}

async function handleSubmit() {
  errorMsg.value = ''
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  const result = await login(username.value, password.value)
  if (!result.success) {
    errorMsg.value = result.error || '登录失败'
  }
}

function togglePassword() {
  showPassword.value = !showPassword.value
}

onMounted(() => {
  canvas = document.getElementById('bgCanvas') as HTMLCanvasElement
  ctx = canvas?.getContext('2d')
  if (canvas && ctx) {
    resize()
    const count = Math.min(Math.floor((canvas.width * canvas.height) / 8000), 120)
    particles = Array.from({ length: count }, () => new Particle(canvas!.width, canvas!.height))
    animate()
    window.addEventListener('resize', resize)
  }
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', resize)
})
</script>

<template>
  <div class="login-page">
    <canvas id="bgCanvas" class="bg-canvas"></canvas>

    <div class="glow-orb glow-1"></div>
    <div class="glow-orb glow-2"></div>

    <div class="auth-wrapper">
      <div class="auth-card">
        <div class="auth-header">
          <div class="logo-area">
            <svg class="logo-icon" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#00f2ff" stroke-width="1.5"/>
              <path d="M2 17l10 5 10-5" stroke="#00f2ff" stroke-width="1.5"/>
              <path d="M2 12l10 5 10-5" stroke="#667eea" stroke-width="1.5"/>
            </svg>
            <div class="logo-text">
              <span class="logo-title">GOLD ETF</span>
              <span class="logo-subtitle">技术分析系统</span>
            </div>
          </div>
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">在线</span>
          </div>
        </div>

        <div class="auth-divider">
          <span class="divider-line"></span>
          <span class="divider-text">登录</span>
          <span class="divider-line"></span>
        </div>

        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="form-group">
            <label class="form-label">
              <svg class="label-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              用户名
            </label>
            <div class="input-wrapper">
              <input
                v-model="username"
                type="text"
                placeholder="请输入用户名"
                autocomplete="username"
              />
              <span class="input-line"></span>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">
              <svg class="label-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              密码
            </label>
            <div class="input-wrapper">
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
              <span class="input-line"></span>
              <button type="button" class="toggle-password" :class="{ show: showPassword }" @click="togglePassword">
                <svg class="eye-open" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg class="eye-closed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>

          <div v-if="errorMsg" class="error-msg">
            <svg style="width:14px;height:14px;flex-shrink:0" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="9" stroke="#ff5370" stroke-width="1.5"/>
              <path d="M10 6v5M10 13.5v.5" stroke="#ff5370" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            {{ errorMsg }}
          </div>

          <CyberButton type="submit" :loading="loading" :disabled="!username || !password">
            登 录
          </CyberButton>

          <div class="auth-footer">
            还没有账号?
            <router-link to="/auth/register">立即注册</router-link>
          </div>
        </form>
      </div>

      <div class="system-info">
        <span>V1.0</span>
        <span class="sys-version">2026</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.bg-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.glow-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(120px);
  z-index: 0;
  pointer-events: none;
}

.glow-1 {
  width: 500px;
  height: 500px;
  top: -100px;
  right: -100px;
  background: radial-gradient(circle, rgba(0, 242, 255, 0.08) 0%, transparent 70%);
  animation: drift1 12s ease-in-out infinite alternate;
}

.glow-2 {
  width: 600px;
  height: 600px;
  bottom: -150px;
  left: -100px;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.1) 0%, transparent 70%);
  animation: drift2 15s ease-in-out infinite alternate;
}

@keyframes drift1 {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(-60px, 40px) scale(1.1); }
}

@keyframes drift2 {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(50px, -30px) scale(1.05); }
}

.auth-wrapper {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 460px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.auth-card {
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  padding: 36px 40px 32px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow:
    0 0 40px rgba(0, 242, 255, 0.05),
    0 25px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  animation: cardEntrance 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
  transform: translateY(30px);
}

@keyframes cardEntrance {
  to { opacity: 1; transform: translateY(0); }
}

.auth-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 14px;
}

.logo-icon {
  width: 44px;
  height: 44px;
  filter: drop-shadow(0 0 12px rgba(0, 242, 255, 0.4));
  animation: logoPulse 4s ease-in-out infinite;
}

@keyframes logoPulse {
  0%, 100% { filter: drop-shadow(0 0 12px rgba(0, 242, 255, 0.4)); }
  50% { filter: drop-shadow(0 0 20px rgba(0, 242, 255, 0.6)); }
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 3px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  letter-spacing: 2px;
  margin-top: 2px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid rgba(0, 242, 255, 0.2);
  border-radius: 20px;
  background: rgba(0, 242, 255, 0.05);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00f2ff;
  box-shadow: 0 0 8px #00f2ff;
  animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-text {
  font-size: 11px;
  color: var(--accent-cyan);
  letter-spacing: 1px;
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-color), transparent);
}

.divider-text {
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 3px;
  text-transform: uppercase;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: var(--text-secondary);
  letter-spacing: 1px;
  cursor: pointer;
}

.label-icon {
  width: 16px;
  height: 16px;
  color: var(--accent-purple);
}

.input-wrapper {
  position: relative;

  input {
    width: 100%;
    padding: 14px 48px 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(102, 126, 234, 0.2);
    border-radius: 10px;
    color: var(--text-primary);
    font-size: 15px;
    outline: none;
    transition: border-color 0.3s, box-shadow 0.3s, background 0.3s;
    letter-spacing: 1px;

    &::placeholder {
      color: var(--text-muted);
      letter-spacing: 1px;
    }

    &:focus {
      border-color: var(--border-active);
      background: rgba(0, 242, 255, 0.03);
      box-shadow: 0 0 20px rgba(0, 242, 255, 0.1), inset 0 0 20px rgba(0, 242, 255, 0.03);

      & ~ .input-line {
        width: 100%;
      }
    }
  }
}

.input-line {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  border-radius: 2px;
  transform: translateX(-50%);
  transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 0 10px var(--accent-cyan);
}

.toggle-password {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--text-muted);
  transition: color 0.2s;

  &:hover { color: var(--text-secondary); }

  svg {
    width: 18px;
    height: 18px;
    display: block;
  }

  .eye-closed { display: none; }

  &.show {
    .eye-open { display: none; }
    .eye-closed { display: block; }
  }
}

.error-msg {
  font-size: 13px;
  color: var(--error-color);
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(255, 83, 112, 0.08);
  border: 1px solid rgba(255, 83, 112, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  animation: shake 0.4s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
}

.auth-footer {
  text-align: center;
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.system-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 1px;
  animation: fadeIn 1s ease 0.5s both;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.sys-version {
  padding: 2px 8px;
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 10px;
  font-size: 10px;
}

@media (max-width: 500px) {
  .auth-card {
    padding: 28px 24px 24px;
  }

  .logo-icon {
    width: 36px;
    height: 36px;
  }

  .logo-title {
    font-size: 14px;
  }

  .status-indicator {
    display: none;
  }
}
</style>
