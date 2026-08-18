<script setup>
import { ref } from 'vue'
import { fetchApi } from '../../api'

const file = ref(null)
const dragging = ref(false)
const loading = ref(false)
const result = ref(null)
const error = ref('')

function onFileChange(event) {
  const selected = event.target.files?.[0]
  if (selected) {
    file.value = selected
    result.value = null
    error.value = ''
  }
}

function onDrop(event) {
  dragging.value = false
  const selected = event.dataTransfer.files?.[0]
  if (selected) {
    file.value = selected
    result.value = null
    error.value = ''
  }
}

function removeFile() {
  file.value = null
  result.value = null
  error.value = ''
}

async function submitImport() {
  if (!file.value) {
    error.value = '请先选择文件'
    return
  }

  loading.value = true
  error.value = ''
  result.value = null

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const res = await fetchApi('/api/admin/funds/import', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || '导入失败')
    }
    result.value = data
  } catch (e) {
    error.value = e.message || '导入失败'
  } finally {
    loading.value = false
  }
}

function downloadTemplate() {
  const headers = [
    '基金代码',
    '市场',
    '基金名称',
    '分类',
    '风险等级',
    '基金经理',
    '成立日期',
    '入选理由',
    '目标客户',
    '标签',
  ]
  const csvContent = '﻿' + headers.join(',') + '\n'
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = '基金批量导入模板.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>

<template>
  <div class="p-6 max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold mb-6">批量导入基金</h1>

    <div class="mb-6 p-4 rounded-xl bg-blue-50 text-blue-700 border border-blue-200">
      <p class="text-sm">
        支持 .xlsx / .xls 格式。必填列：基金代码、分类、风险等级。市场留空默认“场外（OF）”。
        若已配置 Tushare Token，系统会自动补齐基金名称、基金经理、成立日期。
        标签列支持用逗号、分号或顿号分隔，不存在的标签会自动归入“策略/主题”分类。
      </p>
      <button type="button" class="mt-3 text-sm text-brand hover:underline" @click="downloadTemplate">下载 CSV 模板</button>
    </div>

    <div
      class="border-2 border-dashed rounded-2xl p-10 text-center transition-colors"
      :class="dragging ? 'border-brand bg-brand/5' : 'border-hairline bg-surface-soft'"
      @dragenter.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input id="file" type="file" accept=".xlsx,.xls" class="hidden" @change="onFileChange" />
      <label for="file" class="cursor-pointer">
        <p class="text-muted mb-2">点击或拖拽上传 Excel 文件</p>
        <p class="text-xs text-muted">支持 .xlsx / .xls</p>
      </label>
    </div>

    <div v-if="file" class="mt-4 flex items-center justify-between card p-4">
      <div class="flex items-center gap-3">
        <span class="text-2xl">📄</span>
        <div>
          <div class="font-medium">{{ file.name }}</div>
          <div class="text-xs text-muted">{{ (file.size / 1024).toFixed(1) }} KB</div>
        </div>
      </div>
      <button type="button" class="text-sm text-up hover:underline" @click="removeFile">移除</button>
    </div>

    <div v-if="error" class="mt-4 p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">{{ error }}</div>

    <div class="mt-6 flex justify-end">
      <button type="button" class="btn-primary" :disabled="!file || loading" @click="submitImport">
        {{ loading ? '导入中...' : '开始导入' }}
      </button>
    </div>

    <div v-if="result" class="mt-6 card p-5">
      <h2 class="text-lg font-semibold mb-4">导入结果</h2>
      <div class="grid grid-cols-3 gap-4 mb-4">
        <div class="p-4 rounded-xl bg-green-50 text-green-700 text-center">
          <div class="text-2xl font-bold">{{ result.created }}</div>
          <div class="text-sm">新建</div>
        </div>
        <div class="p-4 rounded-xl bg-blue-50 text-blue-700 text-center">
          <div class="text-2xl font-bold">{{ result.updated }}</div>
          <div class="text-sm">更新</div>
        </div>
        <div class="p-4 rounded-xl bg-gray-100 text-gray-600 text-center">
          <div class="text-2xl font-bold">{{ result.skipped }}</div>
          <div class="text-sm">跳过</div>
        </div>
      </div>

      <div v-if="result.errors.length > 0">
        <h3 class="font-medium mb-2">错误信息（{{ result.errors.length }} 条）</h3>
        <ul class="max-h-60 overflow-y-auto text-sm space-y-1 text-red-600">
          <li v-for="(err, idx) in result.errors" :key="idx">• {{ err }}</li>
        </ul>
      </div>
      <div v-else class="text-green-700 text-sm">全部导入成功，无错误。</div>
    </div>
  </div>
</template>
