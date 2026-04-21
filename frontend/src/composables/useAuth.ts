import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export function useAuth() {
  const store = useAuthStore()
  const router = useRouter()

  const user = computed(() => store.user)
  const isAuthenticated = computed(() => store.isAuthenticated)
  const loading = computed(() => store.loading)

  async function login(username: string, password: string) {
    const result = await store.login(username, password)
    if (result.success) {
      router.push('/stock')
    }
    return result
  }

  async function register(username: string, password: string) {
    const result = await store.register(username, password)
    if (result.success) {
      router.push('/stock')
    }
    return result
  }

  async function logout() {
    await store.logout()
    router.push('/auth/login')
  }

  return {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout
  }
}
