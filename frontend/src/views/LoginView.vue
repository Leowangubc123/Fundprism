<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.message || '登录失败'
      return
    }
    auth.login(data.token, data.role, data.username)
    router.push('/overview')
  } catch (e) {
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-canvas px-4">
    <div class="w-full max-w-sm">
      <h1 class="text-2xl font-bold text-center mb-8">基金评价系统</h1>
      <form class="card p-8 space-y-5" @submit.prevent="handleLogin">
        <div>
          <label class="block text-sm font-medium mb-2">用户名</label>
          <input v-model="username" type="text" class="input w-full" placeholder="请输入用户名" required />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">密码</label>
          <input v-model="password" type="password" class="input w-full" placeholder="请输入密码" required />
        </div>
        <p v-if="error" class="text-up text-sm">{{ error }}</p>
        <button type="submit" class="btn-primary w-full" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>
