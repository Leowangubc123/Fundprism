<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { fetchApi } from '../../api'

const tags = ref([])
const loading = ref(false)
const message = ref('')
const error = ref('')
const showModal = ref(false)
const isEditing = ref(false)
const editingTagId = ref(null)

const categoryOptions = [
  { value: '业务属性', label: '业务属性' },
  { value: '策略/主题', label: '策略/主题' },
]

const emptyForm = {
  name: '',
  category: '策略/主题',
  sort_order: 0,
  is_active: true,
}

const form = reactive({ ...emptyForm })
const formErrors = reactive({})

function resetForm() {
  Object.assign(form, emptyForm)
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
}

function openCreate() {
  isEditing.value = false
  editingTagId.value = null
  resetForm()
  showModal.value = true
}

function openEdit(tag) {
  isEditing.value = true
  editingTagId.value = tag.id
  Object.assign(form, {
    name: tag.name,
    category: tag.category,
    sort_order: tag.sort_order ?? 0,
    is_active: tag.is_active,
  })
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function validateForm() {
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  let ok = true
  if (!form.name.trim()) {
    formErrors.name = '请输入标签名称'
    ok = false
  }
  if (!form.category.trim()) {
    formErrors.category = '请选择分类'
    ok = false
  }
  return ok
}

async function submitForm() {
  if (!validateForm()) return
  error.value = ''
  message.value = ''

  const payload = { ...form }
  try {
    if (isEditing.value) {
      const res = await fetchApi(`/api/admin/tags/${editingTagId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('保存失败')
      message.value = '标签已更新'
    } else {
      const res = await fetchApi('/api/admin/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('创建失败')
      message.value = '标签已创建'
    }
    showModal.value = false
    await fetchTags()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

async function fetchTags() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchApi('/api/admin/tags?include_inactive=true')
    if (!res.ok) throw new Error('加载失败')
    tags.value = await res.json()
  } catch (e) {
    error.value = '加载标签失败'
  } finally {
    loading.value = false
  }
}

async function toggleTag(tag) {
  error.value = ''
  message.value = ''
  try {
    const res = await fetchApi(`/api/admin/tags/${tag.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !tag.is_active }),
    })
    if (!res.ok) throw new Error('更新失败')
    message.value = `标签已${tag.is_active ? '停用' : '启用'}`
    await fetchTags()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

onMounted(fetchTags)

const groupedTags = computed(() => {
  const groups = {}
  for (const tag of tags.value) {
    if (!groups[tag.category]) groups[tag.category] = []
    groups[tag.category].push(tag)
  }
  for (const key of Object.keys(groups)) {
    groups[key].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.name.localeCompare(b.name, 'zh-CN'))
  }
  return groups
})
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">标签管理</h1>
      <button type="button" class="btn-primary" @click="openCreate">+ 新增标签</button>
    </div>

    <div v-if="message" class="mb-4 p-4 rounded-xl bg-green-50 text-green-700 border border-green-200">{{ message }}</div>
    <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">{{ error }}</div>

    <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
    <div v-else-if="tags.length === 0" class="text-center py-20 text-muted">暂无标签</div>

    <div v-else class="space-y-6">
      <div v-for="(groupTags, category) in groupedTags" :key="category" class="card p-5">
        <h2 class="text-lg font-semibold mb-4">{{ category }}</h2>
        <div class="flex flex-wrap gap-3">
          <div
            v-for="tag in groupTags"
            :key="tag.id"
            class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm border"
            :class="tag.is_active ? 'bg-surface-strong border-hairline text-body' : 'bg-surface-soft border-hairline text-muted line-through'"
          >
            <span>{{ tag.name }}</span>
            <button type="button" class="text-xs hover:text-brand" @click="openEdit(tag)">编辑</button>
            <button type="button" class="text-xs hover:text-up" @click="toggleTag(tag)">
              {{ tag.is_active ? '停用' : '启用' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-canvas rounded-3xl border border-hairline w-full max-w-md p-6">
        <h2 class="text-xl font-bold mb-6">{{ isEditing ? '编辑标签' : '新增标签' }}</h2>

        <form class="space-y-4" @submit.prevent="submitForm">
          <div>
            <label class="block text-sm font-medium mb-1">标签名称 *</label>
            <input v-model="form.name" type="text" class="input w-full" placeholder="例如：红利主题" />
            <p v-if="formErrors.name" class="text-up text-xs mt-1">{{ formErrors.name }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">分类 *</label>
            <select v-model="form.category" class="input w-full">
              <option v-for="opt in categoryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
            <p v-if="formErrors.category" class="text-up text-xs mt-1">{{ formErrors.category }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">排序（数字越小越靠前）</label>
            <input v-model.number="form.sort_order" type="number" class="input w-full" />
          </div>

          <div class="flex items-center gap-2">
            <input id="is_active" v-model="form.is_active" type="checkbox" class="w-4 h-4 accent-brand" />
            <label for="is_active" class="text-sm">启用</label>
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
