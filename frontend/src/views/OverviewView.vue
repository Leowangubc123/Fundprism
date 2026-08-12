<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const funds = ref([])
const keyword = ref('')
const loading = ref(false)

const selectedIds = ref([])
const canCompare = computed(() => selectedIds.value.length >= 2)
const tooManySelected = computed(() => selectedIds.value.length > 5)

async function fetchFunds() {
  loading.value = true
  try {
    const res = await fetch(`/api/funds?q=${encodeURIComponent(keyword.value)}`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok) throw new Error('加载失败')
    funds.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

function toggleFund(id) {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((x) => x !== id)
  } else if (selectedIds.value.length < 5) {
    selectedIds.value.push(id)
  }
}

function goCompare() {
  if (!canCompare.value) return
  router.push(`/compare?ids=${selectedIds.value.join(',')}`)
}

onMounted(fetchFunds)
</script>

<template>
  <div class="min-h-screen bg-surface-soft">
    <header class="bg-canvas border-b border-hairline px-6 h-16 flex items-center justify-between sticky top-0 z-10">
      <h1 class="font-bold text-lg">基金总览</h1>
      <div class="flex items-center gap-4">
        <span class="text-sm text-body">{{ auth.username }}</span>
        <button class="text-sm text-body hover:text-ink" @click="logout">退出</button>
      </div>
    </header>

    <main class="max-w-6xl mx-auto p-6">
      <div class="flex items-center justify-between mb-6">
        <input v-model="keyword" type="text" class="search-pill w-72" placeholder="搜索基金名称/代码" @keyup.enter="fetchFunds" />
        <div class="flex items-center gap-3">
          <span v-if="selectedIds.length" class="text-sm text-body">
            已选 {{ selectedIds.length }} 只基金
          </span>
          <button class="btn-secondary" @click="fetchFunds">搜索</button>
          <button
            class="btn-primary"
            :disabled="!canCompare || tooManySelected"
            :class="{ 'opacity-50 cursor-not-allowed': !canCompare || tooManySelected }"
            @click="goCompare"
          >
            对比
          </button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="fund in funds"
          :key="fund.id"
          class="card p-5 cursor-pointer hover:shadow-md transition-shadow relative"
          @click="router.push(`/detail/${fund.id}`)"
        >
          <input
            type="checkbox"
            class="absolute top-4 right-4 w-4 h-4 accent-brand"
            :checked="selectedIds.includes(fund.id)"
            @click.stop="toggleFund(fund.id)"
          />
          <div class="flex items-start justify-between mb-3">
            <div>
              <h3 class="font-semibold text-ink">{{ fund.name }}</h3>
              <p class="text-xs text-muted mt-1">{{ fund.code }}</p>
            </div>
            <span class="text-xs px-2 py-1 rounded-full bg-surface-strong text-body">{{ fund.category }}</span>
          </div>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p class="text-muted text-xs">净值</p>
              <p class="font-semibold">{{ fund.nav?.toFixed(4) ?? '-' }}</p>
            </div>
            <div>
              <p class="text-muted text-xs">日涨幅</p>
              <p :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'" class="font-semibold">
                {{ fund.daily_return != null ? `${fund.daily_return >= 0 ? '+' : ''}${fund.daily_return.toFixed(2)}%` : '-' }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
