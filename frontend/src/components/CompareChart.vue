<script setup>
import { computed } from 'vue'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { Line } from 'vue-chartjs'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps({
  funds: { type: Array, default: () => [] },
})

const colors = ['#0052ff', '#cf202f', '#05b169', '#f4b000', '#7c3aed']

const chartData = computed(() => {
  if (!props.funds.length) return { labels: [], datasets: [] }

  const dateSet = new Set()
  props.funds.forEach((fund) => {
    fund.nav_history?.forEach((item) => dateSet.add(item.date))
  })
  const labels = Array.from(dateSet).sort()

  const datasets = props.funds.map((fund, index) => {
    const navMap = new Map(fund.nav_history?.map((item) => [item.date, item.nav]))
    return {
      label: fund.name,
      data: labels.map((date) => navMap.get(date) ?? null),
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length],
      tension: 0.3,
      pointRadius: 2,
    }
  })

  return { labels, datasets }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' } },
  scales: {
    y: { grid: { color: '#eef0f3' }, ticks: { color: '#7c828a' } },
    x: { grid: { display: false }, ticks: { color: '#7c828a' } },
  },
}
</script>

<template>
  <div class="h-[360px]">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
