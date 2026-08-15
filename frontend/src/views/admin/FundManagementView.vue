<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { fetchApi } from '../../api'

const funds = ref([])
const tags = ref([])
const loading = ref(false)
const message = ref('')
const error = ref('')
const showModal = ref(false)
const isEditing = ref(false)
const editingFundId = ref(null)
const syncingId = ref(null)

const marketOptions = [
  { value: 'OF', label: '场外' },
  { value: 'SH', label: '上海（SH）' },
  { value: 'SZ', label: '深圳（SZ）' },
]

const marketLabel = (value) => marketOptions.find((o) => o.value === value)?.label || value

const emptyForm = {
  name: '',
  code: '',
  market: 'OF',
  category: '',
  risk_level: '',
  manager: '',
  establish_date: '',
  reason: '',
  target_clients: '',
  tag_ids: [],
}

const form = reactive({ ...emptyForm })
const formErrors = reactive({})

function resetForm() {
  Object.assign(form, emptyForm)
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
}

function openCreate() {
  isEditing.value = false
  editingFundId.value = null
  resetForm()
  showModal.value = true
}

function openEdit(fund) {
  isEditing.value = true
  editingFundId.value = fund.id
  Object.assign(form, {
    name: fund.name,
    code: fund.code,
    market: fund.market,
    category: fund.category,
    risk_level: fund.risk_level,
    manager: fund.manager || '',
    establish_date: fund.establish_date || '',
    reason: fund.reason || '',
    target_clients: fund.target_clients || '',
    tag_ids: fund.tags?.map((t) => t.id) || [],
  })
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function toggleTag(tagId) {
  const idx = form.tag_ids.indexOf(tagId)
  if (idx >= 0) {
    form.tag_ids.splice(idx, 1)
  } else {
    form.tag_ids.push(tagId)
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

const groupedTags = computed(() => {
  const groups = {}
  for (const tag of tags.value) {
    if (!groups[tag.category]) groups[tag.category] = []
    groups[tag.category].push(tag)
  }
  return groups
})

function validateForm() {
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  let ok = true

  if (!form.name.trim()) {
    formErrors.name = '请输入基金名称'
    ok = false
  }
  if (!/^\d{6}$/.test(form.code)) {
    formErrors.code = '基金代码必须为 6 位数字'
    ok = false
  }
  if (!form.category.trim()) {
    formErrors.category = '请输入分类'
    ok = false
  }
  if (!form.risk_level.trim()) {
    formErrors.risk_level = '请输入风险等级'
    ok = false
  }

  return ok
}

async function submitForm() {
  if (!validateForm()) return

  error.value = ''
  message.value = ''

  const payload = { ...form }
  if (!payload.establish_date) delete payload.establish_date

  try {
    if (isEditing.value) {
      const res = await fetchApi(`/api/admin/funds/${editingFundId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('保存失败')
      message.value = '基金信息已更新'
    } else {
      const res = await fetchApi('/api/admin/funds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('创建失败')
      message.value = '基金已创建'
    }
    showModal.value = false
    await fetchFunds()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

async function lookupFund() {
  error.value = ''
  message.value = ''

  if (!/^\d{6}$/.test(form.code)) {
    error.value = '请先输入 6 位基金代码'
    return
  }

  try {
    const res = await fetchApi(`/api/admin/funds/lookup?code=${form.code}&market=${form.market}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '查询失败')

    if (data.name) form.name = data.name
    if (data.manager) form.manager = data.manager
    if (data.category) form.category = data.category
    if (data.establish_date) form.establish_date = data.establish_date

    message.value = `已获取：${data.name}`
  } catch (e) {
    error.value = e.message || '从 Tushare 获取失败'
  }
}

async function fetchFunds() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchApi('/api/admin/funds')
    if (!res.ok) throw new Error('加载失败')
    funds.value = await res.json()
  } catch (e) {
    error.value = '加载基金列表失败'
  } finally {
    loading.value = false
  }
}

async function deleteFund(fund) {
  if (!confirm(`确定删除“${fund.name}”吗？此操作不可恢复。`)) return

  error.value = ''
  message.value = ''
  try {
    const res = await fetchApi(`/api/admin/funds/${fund.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('删除失败')
    message.value = '基金已删除'
    await fetchFunds()
  } catch (e) {
    error.value = e.message || '删除失败'
  }
}

async function syncFund(fund) {
  error.value = ''
  message.value = ''
  syncingId.value = fund.id
  try {
    const res = await fetchApi(`/api/admin/funds/${fund.id}/sync`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '同步失败')
    message.value = `${fund.name}：${data.message || `同步完成，写入 ${data.records_count} 条`}`
    await fetchFunds()
  } catch (e) {
    error.value = e.message || '同步失败'
  } finally {
    syncingId.value = null
  }
}

onMounted(() => {
  fetchFunds()
  fetchTags()
})

const sortedFunds = computed(() => {
  return [...funds.value].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">基金管理</h1>
      <button type="button" class="btn-primary" @click="openCreate">+ 新增基金</button>
    </div>

    <div v-if="message" class="mb-4 p-4 rounded-xl bg-green-50 text-green-700 border border-green-200">{{ message }}</div>
    <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">{{ error }}</div>

    <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
    <div v-else-if="funds.length === 0" class="text-center py-20 text-muted">暂无基金，点击右上角添加</div>

    <div v-else class="card overflow-hidden">
      <table class="w-full text-left text-sm">
        <thead class="bg-surface-soft">
          <tr class="border-b border-hairline">
            <th class="px-5 py-3 font-semibold">名称</th>
            <th class="px-5 py-3 font-semibold">代码</th>
            <th class="px-5 py-3 font-semibold">市场</th>
            <th class="px-5 py-3 font-semibold">分类</th>
            <th class="px-5 py-3 font-semibold">风险等级</th>
            <th class="px-5 py-3 font-semibold">基金经理</th>
            <th class="px-5 py-3 font-semibold">最新净值日期</th>
            <th class="px-5 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="fund in sortedFunds"
            :key="fund.id"
            class="border-b border-hairline last:border-b-0 hover:bg-surface-soft"
          >
            <td class="px-5 py-4 font-medium">{{ fund.name }}</td>
            <td class="px-5 py-4">{{ fund.code }}</td>
            <td class="px-5 py-4">{{ marketLabel(fund.market) }}</td>
            <td class="px-5 py-4">{{ fund.category }}</td>
            <td class="px-5 py-4">{{ fund.risk_level }}</td>
            <td class="px-5 py-4">{{ fund.manager || '-' }}</td>
            <td class="px-5 py-4">{{ fund.latest_nav_date || '-' }}</td>
            <td class="px-5 py-4 text-right">
              <button type="button" class="text-brand hover:underline mr-3" @click="openEdit(fund)">编辑</button>
              <button
                type="button"
                class="text-brand hover:underline mr-3"
                :disabled="syncingId === fund.id"
                @click="syncFund(fund)"
              >
                {{ syncingId === fund.id ? '同步中...' : '同步' }}
              </button>
              <button type="button" class="text-up hover:underline" @click="deleteFund(fund)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-canvas rounded-3xl border border-hairline w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <h2 class="text-xl font-bold mb-6">{{ isEditing ? '编辑基金' : '新增基金' }}</h2>

        <form class="space-y-4" @submit.prevent="submitForm">
          <div>
            <label class="block text-sm font-medium mb-1">基金名称 *</label>
            <input v-model="form.name" type="text" class="input w-full" placeholder="例如：易方达蓝筹精选混合" />
            <p v-if="formErrors.name" class="text-up text-xs mt-1">{{ formErrors.name }}</p>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">基金代码 *</label>
              <input
                v-model="form.code"
                type="text"
                maxlength="6"
                :disabled="isEditing"
                class="input w-full"
                placeholder="6位数字"
              />
              <p v-if="formErrors.code" class="text-up text-xs mt-1">{{ formErrors.code }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">市场 *</label>
              <select v-model="form.market" class="input w-full" :disabled="isEditing">
                <option v-for="opt in marketOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
          </div>

          <div v-if="!isEditing" class="flex justify-end">
            <button type="button" class="text-sm text-brand hover:underline" @click="lookupFund">
              从 Tushare 获取基本信息
            </button>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">分类 *</label>
              <input v-model="form.category" type="text" class="input w-full" placeholder="例如：混合型" />
              <p v-if="formErrors.category" class="text-up text-xs mt-1">{{ formErrors.category }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">风险等级 *</label>
              <input v-model="form.risk_level" type="text" class="input w-full" placeholder="例如：中" />
              <p v-if="formErrors.risk_level" class="text-up text-xs mt-1">{{ formErrors.risk_level }}</p>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">基金经理</label>
            <input v-model="form.manager" type="text" class="input w-full" placeholder="可选" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">成立日期</label>
            <input v-model="form.establish_date" type="date" class="input w-full" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">入选理由</label>
            <textarea v-model="form.reason" rows="3" class="input w-full" placeholder="可选"></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">目标客户</label>
            <input v-model="form.target_clients" type="text" class="input w-full" placeholder="可选" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">标签</label>
            <div v-if="tags.length === 0" class="text-sm text-muted">暂无可用标签，请先到“标签管理”添加</div>
            <div v-else class="space-y-3">
              <div v-for="(group, category) in groupedTags" :key="category">
                <div class="text-xs text-muted mb-1">{{ category }}</div>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="tag in group"
                    :key="tag.id"
                    type="button"
                    class="px-3 py-1 rounded-full text-sm border transition-colors"
                    :class="form.tag_ids.includes(tag.id) ? 'bg-brand text-white border-brand' : 'bg-surface-strong border-hairline text-body hover:border-brand'"
                    @click="toggleTag(tag.id)"
                  >
                    {{ tag.name }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary">{{ isEditing ? '保存' : '创建' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
