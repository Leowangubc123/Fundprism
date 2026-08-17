<script setup>
import { ref, onMounted } from 'vue'
import { fetchApi } from '../../api'

const logs = ref([])
const loading = ref(false)
const running = ref(false)
const message = ref('')
const error = ref('')

async function fetchLogs() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchApi('/api/admin/sync-logs')
    if (!res.ok) throw new Error('加载失败')
    logs.value = await res.json()
  } catch (e) {
    error.value = '加载同步日志失败'
  } finally {
    loading.value = false
  }
}

async function runSync() {
  if (!confirm('确定立即为所有基金同步最新净值吗？')) return
  running.value = true
  error.value = ''
  message.value = ''
  try {
    const res = await fetchApi('/api/admin/sync/run', { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '同步失败')
    message.value = data.message
    await fetchLogs()
  } catch (e) {
    error.value = e.message || '同步失败'
  } finally {
    running.value = false
  }
}

function statusClass(status) {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-700 border-green-200'
    case 'failed':
      return 'bg-red-100 text-red-700 border-red-200'
    case 'running':
      return 'bg-blue-100 text-blue-700 border-blue-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function statusLabel(status) {
  switch (status) {
    case 'success':
      return '成功'
    case 'failed':
      return '失败'
    case 'running':
      return '进行中'
    case 'skipped':
      return '跳过'
    default:
      return status
  }
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(fetchLogs)
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold">同步日志</h1>
        <p class="text-sm text-muted mt-1">系统每天凌晨 2:00 自动同步全部基金净值，也可手动触发。</p>
      </div>
      <button type="button" class="btn-primary" :disabled="running" @click="runSync">
        {{ running ? '同步中...' : '立即同步全部' }}
      </button>
    </div>

    <div v-if="message" class="mb-4 p-4 rounded-xl bg-green-50 text-green-700 border border-green-200">{{ message }}</div>
    <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">{{ error }}</div>

    <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
    <div v-else-if="logs.length === 0" class="text-center py-20 text-muted">暂无同步记录</div>

    <div v-else class="card overflow-hidden">
      <table class="w-full text-left text-sm">
        <thead class="bg-surface-soft">
          <tr class="border-b border-hairline">
            <th class="px-5 py-3 font-semibold">类型</th>
            <th class="px-5 py-3 font-semibold">基金</th>
            <th class="px-5 py-3 font-semibold">状态</th>
            <th class="px-5 py-3 font-semibold">记录数</th>
            <th class="px-5 py-3 font-semibold">失败数</th>
            <th class="px-5 py-3 font-semibold">开始时间</th>
            <th class="px-5 py-3 font-semibold">结束时间</th>
            <th class="px-5 py-3 font-semibold">错误信息</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.id"
            class="border-b border-hairline last:border-b-0 hover:bg-surface-soft"
          >
            <td class="px-5 py-4">{{ log.sync_type === 'daily_sync' ? '全量同步' : '单基金同步' }}</td>
            <td class="px-5 py-4">{{ log.fund_name || '-' }}</td>
            <td class="px-5 py-4">
              <span class="text-xs px-2 py-1 rounded-full border" :class="statusClass(log.status)">
                {{ statusLabel(log.status) }}
              </span>
            </td>
            <td class="px-5 py-4">{{ log.records_count }}</td>
            <td class="px-5 py-4">{{ log.failed_records }}</td>
            <td class="px-5 py-4">{{ formatDate(log.started_at) }}</td>
            <td class="px-5 py-4">{{ formatDate(log.ended_at) }}</td>
            <td class="px-5 py-4 max-w-xs truncate" :title="log.error_message">{{ log.error_message || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
