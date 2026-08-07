import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import LoginView from './views/LoginView.vue'
import OverviewView from './views/OverviewView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', redirect: '/overview' },
    { path: '/overview', name: 'overview', component: OverviewView, meta: { requiresAuth: true } },
    { path: '/compare', name: 'compare', component: () => import('./views/CompareView.vue'), meta: { requiresAuth: true } },
    { path: '/detail/:id', name: 'detail', component: () => import('./views/DetailView.vue'), meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: () => import('./views/admin/AdminLayout.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.meta.requiresAdmin && auth.role !== 'admin') {
    return { name: 'overview' }
  }
})

export default router
