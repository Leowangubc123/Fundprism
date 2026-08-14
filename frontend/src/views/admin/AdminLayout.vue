<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { path: '/admin/funds', label: '基金管理' },
]

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen flex">
    <!-- Sidebar -->
    <aside class="w-64 bg-surface-dark text-on-dark flex flex-col">
      <div class="h-16 flex items-center px-6 border-b border-white/10">
        <span class="font-bold text-lg">Fundprism 后台</span>
      </div>

      <nav class="flex-1 py-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'block px-6 py-3 text-sm transition-colors',
            isActive(item.path) ? 'bg-white/10 text-white font-medium' : 'text-on-dark-soft hover:text-white hover:bg-white/5',
          ]"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="p-4 border-t border-white/10">
        <div class="text-sm text-on-dark-soft mb-3">{{ auth.username }}</div>
        <button
          type="button"
          class="w-full text-left text-sm text-on-dark-soft hover:text-white"
          @click="logout"
        >
          退出登录
        </button>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 bg-surface-soft min-h-screen">
      <RouterView />
    </main>
  </div>
</template>
