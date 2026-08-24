<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'
import { fetchApi } from '../api'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const fund = ref(null)
const materials = ref([])
const navHistory = ref([])
const loading = ref(false)
const error = ref('')

const tierOptions = [
  { value: '主推', label: '主推', class: 'bg-green-100 text-green-700 border-green-200' },
  { value: '备选', label: '备选', class: 'bg-blue-100 text-blue-700 border-blue-200' },
  { value: '替代', label: '替代', class: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  { value: '观察', label: '观察', class: 'bg-gray-100 text-gray-600 border-gray-200' },
]

const tierLabel = (value) => tierOptions.find((o) => o.value === value)?.label || value
const tierClass = (value) => tierOptions.find((o) => o.value === value)?.class || 'bg-surface-strong text-body border-hairline'

function formatReturn(value) {
  if (value == null) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function formatDate(value) {
  if (!value) return '-'
  return value
}

function managerTenure(startDate) {
  if (!startDate) return '-'
  const start = new Date(startDate)
  const now = new Date()
  const years = (now - start) / (1000 * 60 * 60 * 24 * 365.25)
  return `${Math.floor(years * 10) / 10} 年`
}

const assetItems = computed(() => {
  if (!fund.value) return []
  return [
    { key: 'asset_stock_pct', label: '股票', color: 'bg-up' },
    { key: 'asset_bond_pct', label: '债券', color: 'bg-blue-500' },
    { key: 'asset_cash_pct', label: '现金', color: 'bg-yellow-500' },
    { key: 'asset_other_pct', label: '其他', color: 'bg-gray-400' },
  ].map((item) => ({
    ...item,
    value: fund.value[item.key] ?? 0,
  }))
})

const chartData = computed(() => ({
  labels: navHistory.value.map((item) => item.date),
  datasets: [{
    label: '单位净值',
    data: navHistory.value.map((item) => item.nav),
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
    const [fundRes, navRes, materialsRes] = await Promise.all([
      fetchApi(`/api/funds/${route.params.id}`),
      fetchApi(`/api/funds/${route.params.id}/nav`),
      fetchApi(`/api/funds/${route.params.id}/materials`),
    ])
    if (!fundRes.ok || !navRes.ok) throw new Error('加载失败')
    fund.value = await fundRes.json()
    navHistory.value = await navRes.json()
    if (materialsRes.ok) {
      materials.value = await materialsRes.json()
    }
  } catch (e) {
    error.value = '加载基金详情失败'
  } finally {
    loading.value = false
  }
}

async function downloadMaterial(material) {
  try {
    const res = await fetchApi(`/api/funds/materials/${material.id}/download`, { method: 'POST' })
    if (!res.ok) throw new Error('下载失败')
    const data = await res.json()
    if (data.download_url) {
      window.open(data.download_url, '_blank')
    }
  } catch (e) {
    error.value = e.message || '下载失败'
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
      <!-- Header card -->
      <div class="card p-6">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap mb-2">
              <h2 class="text-xl font-bold">{{ fund.name }}</h2>
              <span
                v-if="fund.current_tier"
                class="text-xs px-2 py-1 rounded-full border"
                :class="tierClass(fund.current_tier)"
              >
                {{ tierLabel(fund.current_tier) }}
              </span>
            </div>
            <div class="flex items-center gap-2 flex-wrap text-sm text-muted">
              <span class="font-medium text-ink">{{ fund.code }}</span>
              <span v-for="c in fund.codes?.filter((c) => !c.is_primary)" :key="c.id" class="px-1.5 py-0.5 rounded bg-surface-soft border border-hairline">
                {{ c.code }}
              </span>
            </div>
            <div class="flex items-center gap-2 flex-wrap mt-3">
              <span class="text-xs px-2 py-1 rounded-full bg-surface-soft text-body border border-hairline">{{ fund.category }}</span>
              <span class="text-xs px-2 py-1 rounded-full bg-surface-soft text-body border border-hairline">风险：{{ fund.risk_level || '-' }}</span>
            </div>
            <div v-if="fund.tags?.length" class="flex flex-wrap gap-1.5 mt-3">
              <span
                v-for="tag in fund.tags"
                :key="tag.id"
                class="text-xs px-2 py-0.5 rounded-full bg-brand/10 text-brand border border-brand/20"
              >
                {{ tag.name }}
              </span>
            </div>
          </div>
          <div class="text-right shrink-0">
            <p class="text-2xl font-bold">{{ fund.nav?.toFixed(4) ?? '-' }}</p>
            <p :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'" class="text-sm font-medium">
              {{ formatReturn(fund.daily_return) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Metrics grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">近1年收益</p>
          <p :class="fund.return_1y >= 0 ? 'text-up' : 'text-down'" class="font-semibold">{{ formatReturn(fund.return_1y) }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">近3年收益</p>
          <p :class="fund.return_3y >= 0 ? 'text-up' : 'text-down'" class="font-semibold">{{ formatReturn(fund.return_3y) }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">夏普比率</p>
          <p class="font-semibold">{{ fund.sharpe?.toFixed(2) ?? '-' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">最大回撤</p>
          <p class="font-semibold">{{ fund.max_drawdown != null ? `${(fund.max_drawdown * 100).toFixed(2)}%` : '-' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">规模</p>
          <p class="font-semibold">{{ fund.aum != null ? `${(fund.aum / 1e8).toFixed(2)} 亿` : '-' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">排名百分位</p>
          <p class="font-semibold">{{ fund.rank_percentile != null ? `${(fund.rank_percentile * 100).toFixed(0)}%` : '-' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">基金经理</p>
          <p class="font-semibold truncate">{{ fund.manager || '-' }}</p>
        </div>
        <div class="card p-4">
          <p class="text-xs text-muted mb-1">任职年限</p>
          <p class="font-semibold">{{ managerTenure(fund.manager_start_date) }}</p>
        </div>
      </div>

      <!-- Manager & dates -->
      <div class="card p-6">
        <h3 class="font-semibold mb-4">基金经理</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p class="text-muted text-xs">姓名</p>
            <p class="font-medium">{{ fund.manager || '-' }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">任职开始日期</p>
            <p class="font-medium">{{ formatDate(fund.manager_start_date) }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">成立日期</p>
            <p class="font-medium">{{ formatDate(fund.establish_date) }}</p>
          </div>
        </div>
      </div>

      <!-- Reason & target clients -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="card p-6">
          <h3 class="font-semibold mb-3">推荐理由</h3>
          <p class="text-sm text-body whitespace-pre-line leading-relaxed">{{ fund.reason || '暂无' }}</p>
        </div>
        <div class="card p-6">
          <h3 class="font-semibold mb-3">适用客群</h3>
          <p class="text-sm text-body whitespace-pre-line leading-relaxed">{{ fund.target_clients || '暂无' }}</p>
        </div>
      </div>

      <!-- Asset allocation -->
      <div class="card p-6">
        <h3 class="font-semibold mb-4">底层资产分布</h3>
        <div v-if="assetItems.some((i) => i.value > 0)" class="space-y-4">
          <div v-for="item in assetItems" :key="item.key" class="space-y-1">
            <div class="flex justify-between text-sm">
              <span class="text-body">{{ item.label }}</span>
              <span class="font-medium">{{ item.value.toFixed(0) }}%</span>
            </div>
            <div class="h-2 w-full bg-surface-soft rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="item.color"
                :style="{ width: `${Math.min(item.value, 100)}%` }"
              ></div>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-muted">暂无资产配置数据</p>
      </div>

      <!-- Materials -->
      <div v-if="materials.length" class="card p-6">
        <h3 class="font-semibold mb-4">营销物料</h3>
        <div class="space-y-3">
          <div
            v-for="material in materials"
            :key="material.id"
            class="flex items-center justify-between p-3 rounded-xl bg-surface-soft border border-hairline"
          >
            <div>
              <p class="font-medium text-sm">{{ material.name }}</p>
              <p class="text-xs text-muted">{{ material.material_type }}</p>
            </div>
            <button
              type="button"
              class="text-sm text-brand hover:underline"
              @click="downloadMaterial(material)"
            >
              下载
            </button>
          </div>
        </div>
      </div>

      <!-- NAV chart -->
      <div class="card p-6">
        <h3 class="font-semibold mb-4">净值走势</h3>
        <div class="h-80">
          <Line :data="chartData" :options="chartOptions" />
        </div>
      </div>
    </main>
  </div>
</template>
