<script setup>
defineProps({
  funds: { type: Array, default: () => [] },
})

function formatReturn(value) {
  if (value == null) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm text-left">
      <thead class="text-muted border-b border-hairline">
        <tr>
          <th class="py-3 pr-4 font-medium">指标</th>
          <th v-for="fund in funds" :key="fund.id" class="py-3 px-4 font-medium min-w-[140px]">
            {{ fund.name }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">基金代码</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.code }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">类别</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.category }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">最新净值</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4 font-semibold">{{ fund.nav?.toFixed(4) ?? '-' }}</td>
        </tr>
        <tr class="border-b border-hairline-soft">
          <td class="py-3 pr-4 text-muted">日涨幅</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">
            <span v-if="fund.daily_return != null" :class="fund.daily_return >= 0 ? 'text-up' : 'text-down'">
              {{ formatReturn(fund.daily_return) }}
            </span>
            <span v-else class="text-muted">-</span>
          </td>
        </tr>
        <tr>
          <td class="py-3 pr-4 text-muted">基金经理</td>
          <td v-for="fund in funds" :key="fund.id" class="py-3 px-4">{{ fund.manager ?? '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
