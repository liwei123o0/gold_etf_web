import { ref, watch } from 'vue'

const STORAGE_KEY = 'global_settings'

interface GlobalSettings {
  realtimeInterval: number    // 实时行情轮询间隔(ms)
  simRealtimeInterval: number // 模拟交易行情轮询间隔(ms)
}

const DEFAULT_SETTINGS: GlobalSettings = {
  realtimeInterval: 60000,
  simRealtimeInterval: 90000,
}

function loadFromStorage(): GlobalSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch {}
  return { ...DEFAULT_SETTINGS }
}

function saveToStorage(settings: GlobalSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch {}
}

export function useGlobalSettings() {
  const settings = ref<GlobalSettings>(loadFromStorage())

  watch(settings, (val) => {
    saveToStorage(val)
  }, { deep: true })

  function updateSetting<K extends keyof GlobalSettings>(key: K, value: GlobalSettings[K]) {
    settings.value[key] = value
  }

  return {
    settings,
    updateSetting,
  }
}
