import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/stock'
  },
  {
    path: '/auth',
    redirect: '/auth/login'
  },
  {
    path: '/auth/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true }
  },
  {
    path: '/auth/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true }
  },
  {
    path: '/stock',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/simulation',
    name: 'Simulation',
    component: () => import('@/views/SimulationView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 如果有 token 但没有 user，先获取用户信息
  if (authStore.token && !authStore.user) {
    await authStore.fetchUser()
  }

  // 需要登录的路由
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      return next('/auth/login')
    }
  }

  // 游客路由（登录/注册）已登录则跳转到 stock
  if (to.meta.guest && authStore.isAuthenticated) {
    return next('/stock')
  }

  next()
})

export default router
