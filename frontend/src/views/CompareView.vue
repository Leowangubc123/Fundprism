<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import CompareMetrics from '../components/CompareMetrics.vue'
import CompareChart from '../components/CompareChart.vue'
import { fetchApi } from '../api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const funds = ref([])
const loading = ref(false)
const error = ref('')

const selectedIds = computed(() => {
  const raw = route.query.ids || ''
  return String(raw).split(',').filter(Boolean)
})

async function fetchCompareData() {
  if (!selectedIds.value.length) {
    funds.value = []
    error.value = '请先选择要对比的基金'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await fetchApi(`/api/funds/compare?ids=${selectedIds.value.join(',')}`)
    if (!res.ok) throw new Error('加载失败')
    const data = await res.json()
    funds.value = data.funds || []
  } catch (e) {
    console.error(e)
    error.value = '加载对比数据失败'
  } finally {
    loading.value = false
  }
}

function removeFund(id) {
  const ids = selectedIds.value.filter((x) => x !== id)
  router.replace({ path: '/compare', query: { ids: ids.join(',') } })
}

onMounted(fetchCompareData)
watch(() => route.query.ids, fetchCompareData)
</script>

<template>
  <div class="min-h-screen bg-surface-soft">
    <header class="bg-canvas border-b border-hairline px-6 h-16 flex items-center justify-between sticky top-0 z-10">
      <div class="flex items-center gap-4">
        <button type="button" class="text-sm text-body hover:text-ink" @click="router.push('/overview')">← 返回总览</button>
        <h1 class="font-bold text-lg">基金对比</h1>
      </div>
      <button type="button" class="btn-secondary" @click="router.push('/overview')">重新选择</button>
    </header>

    <main class="max-w-6xl mx-auto p-6 space-y-6">
      <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
      <div v-else-if="error" class="text-center py-20 text-up">{{ error }}</div>
      <template v-else-if="funds.length">
        <div class="card p-6">
          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <span class="text-sm text-muted">已选基金：</span>
            <span
              v-for="fund in funds"
              :key="fund.id"
              class="inline-flex items-center gap-1 text-sm px-3 py-1 rounded-full bg-surface-strong"
            >
              {{ fund.name }}
              <button type="button" class="text-muted hover:text-up" @click="removeFund(fund.id)">×</button>
            </span>
          </div>
          <CompareMetrics :funds="funds" />
        </div>

        <div class="card p-6">
          <h3 class="font-semibold mb-4">净值走势对比</h3>
          <CompareChart :funds="funds" />
        </div>
      </template>
    </main>
  </div>
</template>
