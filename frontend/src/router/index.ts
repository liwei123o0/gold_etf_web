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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async () => {
  const authStore = useAuthStore()
  if (authStore.token && !authStore.user) {
    await authStore.fetchUser()
  }
})

export default router
