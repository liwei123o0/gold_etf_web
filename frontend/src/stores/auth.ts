import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authService, type User } from '@/services/authService'

const storedUser = localStorage.getItem('user')
const storedToken = localStorage.getItem('token')

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(storedUser ? JSON.parse(storedUser) : null)
  const token = ref<string | null>(storedToken)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  function setAuth(userData: User, authToken?: string) {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
    if (authToken) {
      token.value = authToken
      localStorage.setItem('token', authToken)
    }
  }

  function clearAuth() {
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const response = await authService.login({ username, password })
      if (response.success && response.user) {
        setAuth(response.user, response.token || undefined)
        return { success: true }
      }
      return { success: false, error: response.error }
    } catch (error: any) {
      return { success: false, error: error.response?.data?.error || '登录失败' }
    } finally {
      loading.value = false
    }
  }

  async function register(username: string, password: string) {
    loading.value = true
    try {
      const response = await authService.register({ username, password })
      if (response.success && response.user) {
        setAuth(response.user, response.token || undefined)
        return { success: true }
      }
      return { success: false, error: response.error }
    } catch (error: any) {
      return { success: false, error: error.response?.data?.error || '注册失败' }
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authService.logout()
    } catch {
      // ignore
    } finally {
      clearAuth()
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const response = await authService.getMe()
      if (response.success && response.user) {
        user.value = response.user
      } else {
        clearAuth()
      }
    } catch {
      clearAuth()
    }
  }

  return {
    user,
    token,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUser,
    setAuth,
    clearAuth
  }
})
