import { ref, onMounted, onUnmounted } from 'vue'

export function useClock() {
  const currentTime = ref('')
  let intervalId: number | null = null

  function updateClock() {
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const year = now.getFullYear()
    const month = pad(now.getMonth() + 1)
    const day = pad(now.getDate())
    const hour = pad(now.getHours())
    const minute = pad(now.getMinutes())
    const second = pad(now.getSeconds())
    currentTime.value = `${year}年${month}月${day}日 ${hour}:${minute}:${second}`
  }

  onMounted(() => {
    updateClock()
    intervalId = window.setInterval(updateClock, 1000)
  })

  onUnmounted(() => {
    if (intervalId) {
      clearInterval(intervalId)
    }
  })

  return { currentTime }
}
