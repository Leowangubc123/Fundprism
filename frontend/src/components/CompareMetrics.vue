<script setup>
defineProps({
  funds: { type: Array, default: () => [] },
})

function getReturnClass(value) {
  if (value == null) return 'text-muted'
  const num = Number(value)
  if (Number.isNaN(num)) return 'text-muted'
  return num >= 0 ? 'text-up' : 'text-down'
}

function formatReturn(value) {
  if (value == null) return '-'
  const num = Number(value)
  if (Number.isNaN(num)) return '-'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function formatNav(value) {
  if (value == null) return '-'
  const num = Number(value)
  return Number.isNaN(num) ? '-' : num.toFixed(4)
}

const metrics = [
  { key: 'code', label: '基金代码', format: (v) => v ?? '-' },
  { key: 'category', label: '类别', format: (v) => v ?? '-' },
  { key: 'nav', label: '最新净值', format: formatNav, isNav: true },
  { key: 'daily_return', label: '日涨幅', format: formatReturn, isReturn: true },
  { key: 'manager', label: '基金经理', format: (v) => v ?? '-' },
]
</script>

<template>
  <div v-if="funds.length" class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-muted border-b border-hairline">
        <tr>
          <th scope="col" class="py-3 pr-4 font-medium">指标</th>
          <th v-for="fund in funds" :key="fund.id" scope="col" class="py-3 px-4 font-medium min-w-[140px]">
            {{ fund.name }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="metric in metrics" :key="metric.key" class="border-b border-hairline-soft">
          <th scope="row" class="py-3 pr-4 text-muted font-normal">{{ metric.label }}</th>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">
            <span v-if="metric.isReturn" :class="getReturnClass(fund[metric.key])">
              {{ metric.format(fund[metric.key]) }}
            </span>
            <span v-else-if="metric.isNav" class="font-semibold">{{ metric.format(fund[metric.key]) }}</span>
            <span v-else>{{ metric.format(fund[metric.key]) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else class="text-center text-muted py-8">请选择基金进行对比</p>
</template>
