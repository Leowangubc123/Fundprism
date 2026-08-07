<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const fund = ref(null)
const navHistory = ref([])
const loading = ref(false)
const error = ref('')

const chartData = computed(() => ({
  labels: navHistory.value.map(item => item.date),
  datasets: [{
    label: '单位净值',
    data: navHistory.value.map(item => item.nav),
    borderColor: '#0052ff',
    backgroundColor: 'rgba(0, 82, 255, 0.1)',
    fill: true,
    tension: 0.3,
  }],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    y: { grid: { color: '#eef0f3' }, ticks: { color: '#7c828a' } },
    x: { grid: { display: false }, ticks: { color: '#7c828a' } },
  },
}

async function fetchDetail() {
  loading.value = true
  error.value = ''
  try {
    const [fundRes, navRes] = await Promise.all([
      fetch(`/api/funds/${route.params.id}`, { headers: { Authorization: `Bearer ${auth.token}` } }),
      fetch(`/api/funds/${route.params.id}/nav`, { headers: { Authorization: `Bearer ${auth.token}` } }),
    ])
    if (!fundRes.ok || !navRes.ok) throw new Error('加载失败')
    fund.value = await fundRes.json()
    navHistory.value = await navRes.json()
  } catch (e) {
    error.value = '加载基金详情失败'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)
</script>

<template>
  <div class="min-h-screen bg-surface-soft">
    <header class="bg-canvas border-b border-hairline px-6 h-16 flex items-center gap-4 sticky top-0 z-10">
      <button class="text-sm text-body hover:text-ink" @click="router.back()">← 返回</button>
      <h1 class="font-bold text-lg">基金详情</h1>
    </header>

    <main v-if="loading" class="text-center py-20 text-muted">加载中...</main>
    <main v-else-if="error" class="text-center py-20 text-up">{{ error }}</main>
    <main v-else-if="fund" class="max-w-4xl mx-auto p-6 space-y-6">
      <div class="card p-6">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-xl font-bold">{{ fund.name }}</h2>
            <p class="text-sm text-muted mt-1">{{ fund.code }} · {{ fund.category }}</p>
          </div>
          <div class="text-right">
            <p class="text-2xl font-bold">{{ fund.nav?.toFixed(4) }}</p>
            <p :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'" class="text-sm font-medium">
              {{ fund.daily_return >= 0 ? '+' : '' }}{{ fund.daily_return?.toFixed(2) }}%
            </p>
          </div>
        </div>
      </div>

      <div class="card p-6">
        <h3 class="font-semibold mb-4">净值走势</h3>
        <div class="h-80">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>
    </main>
  </div>
</template>
