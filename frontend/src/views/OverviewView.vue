<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { fetchApi } from '../api'

const router = useRouter()
const auth = useAuthStore()

const funds = ref([])
const tags = ref([])
const keyword = ref('')
const selectedTag = ref('')
const loading = ref(false)
const error = ref('')

const selectedIds = ref([])
const selectedSet = computed(() => new Set(selectedIds.value))
const isCompareDisabled = computed(() => selectedIds.value.length < 2)

async function fetchFunds() {
  loading.value = true
  error.value = ''
  try {
    let url = `/api/funds?q=${encodeURIComponent(keyword.value.trim())}`
    if (selectedTag.value) {
      url += `&tag=${encodeURIComponent(selectedTag.value)}`
    }
    const res = await fetchApi(url)
    if (!res.ok) throw new Error('加载失败')
    funds.value = await res.json()
  } catch (e) {
    console.error(e)
    error.value = '加载基金数据失败'
  } finally {
    loading.value = false
  }
}

async function fetchTags() {
  try {
    const res = await fetchApi('/api/admin/tags')
    if (!res.ok) throw new Error('加载标签失败')
    tags.value = await res.json()
  } catch (e) {
    console.error(e)
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
    selectedIds.value = [...selectedIds.value, id]
  }
}

function goCompare() {
  if (isCompareDisabled.value) return
  router.push(`/compare?ids=${selectedIds.value.join(',')}`)
}

function formatReturn(value) {
  if (value == null) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

const groupedTags = computed(() => {
  const groups = {}
  for (const tag of tags.value) {
    if (!groups[tag.category]) groups[tag.category] = []
    groups[tag.category].push(tag)
  }
  return groups
})

onMounted(() => {
  fetchFunds()
  fetchTags()
})
</script>

<template>
  <div class="min-h-screen bg-surface-soft">
    <header class="bg-canvas border-b border-hairline px-6 h-16 flex items-center justify-between sticky top-0 z-10">
      <h1 class="font-bold text-lg">基金总览</h1>
      <div class="flex items-center gap-4">
        <RouterLink
          v-if="auth.isAdmin"
          to="/admin/funds"
          class="text-sm text-body hover:text-ink"
        >
          后台管理
        </RouterLink>
        <span class="text-sm text-body">{{ auth.username }}</span>
        <button type="button" class="text-sm text-body hover:text-ink" @click="logout">退出</button>
      </div>
    </header>

    <main class="max-w-6xl mx-auto p-6">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <input v-model="keyword" type="text" class="search-pill w-72" placeholder="搜索基金名称/代码" aria-label="搜索基金名称或代码" @keyup.enter="fetchFunds" />
          <select v-model="selectedTag" class="input w-48" @change="fetchFunds">
            <option value="">全部标签</option>
            <optgroup v-for="(group, category) in groupedTags" :key="category" :label="category">
              <option v-for="tag in group" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
            </optgroup>
          </select>
        </div>
        <div class="flex items-center gap-3">
          <span v-if="selectedIds.length" class="text-sm text-body">
            已选 {{ selectedIds.length }} 只基金
          </span>
          <span v-if="selectedIds.length" class="text-sm text-muted">
            最多选择 5 只基金
          </span>
          <button type="button" class="btn-secondary" @click="fetchFunds">搜索</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="isCompareDisabled"
            :class="{ 'opacity-50 cursor-not-allowed': isCompareDisabled }"
            @click="goCompare"
          >
            对比
          </button>
        </div>
      </div>

      <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
      <div v-else-if="error" class="text-center py-20 text-error">{{ error }}</div>
      <div v-else-if="funds.length === 0" class="text-center py-20 text-muted">未找到基金</div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="fund in funds"
          :key="fund.id"
          class="card p-5 hover:shadow-md transition-shadow relative"
        >
          <RouterLink :to="`/detail/${fund.id}`" class="block h-full">
            <div class="flex items-start justify-between mb-3">
              <div>
                <h3 class="font-semibold text-ink">{{ fund.name }}</h3>
                <p class="text-xs text-muted mt-1">{{ fund.code }}</p>
              </div>
              <span class="text-xs px-2 py-1 rounded-full bg-surface-strong text-body">{{ fund.category }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm mb-3">
              <div>
                <p class="text-muted text-xs">净值</p>
                <p class="font-semibold">{{ fund.nav?.toFixed(4) ?? '-' }}</p>
              </div>
              <div>
                <p class="text-muted text-xs">日涨幅</p>
                <p :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'" class="font-semibold">
                  {{ formatReturn(fund.daily_return) }}
                </p>
              </div>
            </div>
            <div v-if="fund.tags?.length" class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in fund.tags"
                :key="tag.id"
                class="text-xs px-2 py-0.5 rounded-full bg-surface-soft text-body border border-hairline"
              >
                {{ tag.name }}
              </span>
            </div>
          </RouterLink>
          <input
            type="checkbox"
            class="absolute top-4 right-4 w-4 h-4 accent-brand z-10"
            :aria-label="`选择 ${fund.name}`"
            :checked="selectedSet.has(fund.id)"
            @change.stop="toggleFund(fund.id)"
          />
        </div>
      </div>
    </main>
  </div>
</template>
