<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { fetchApi } from '../../api'

const auth = useAuthStore()
const users = ref([])
const loading = ref(false)
const message = ref('')
const error = ref('')
const showModal = ref(false)
const showResetModal = ref(false)
const isEditing = ref(false)
const editingUserId = ref(null)
const resettingUser = ref(null)

const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'sales', label: '销售' },
]

const emptyForm = {
  username: '',
  full_name: '',
  password: '',
  role: 'sales',
  is_active: true,
}

const form = reactive({ ...emptyForm })
const formErrors = reactive({})

const resetFormData = reactive({ password: '' })
const resetFormErrors = reactive({})

function resetForm() {
  Object.assign(form, emptyForm)
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
}

function openCreate() {
  isEditing.value = false
  editingUserId.value = null
  resetForm()
  showModal.value = true
}

function openEdit(user) {
  isEditing.value = true
  editingUserId.value = user.id
  Object.assign(form, {
    username: user.username,
    full_name: user.full_name || '',
    password: '',
    role: user.role,
    is_active: user.is_active,
  })
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function openReset(user) {
  resettingUser.value = user
  resetFormData.password = ''
  Object.keys(resetFormErrors).forEach((k) => delete resetFormErrors[k])
  showResetModal.value = true
}

function closeResetModal() {
  showResetModal.value = false
  resettingUser.value = null
}

function validateForm() {
  Object.keys(formErrors).forEach((k) => delete formErrors[k])
  let ok = true
  if (!form.username.trim() || form.username.trim().length < 2) {
    formErrors.username = '用户名至少 2 个字符'
    ok = false
  }
  if (!isEditing.value && form.password.length < 6) {
    formErrors.password = '密码至少 6 位'
    ok = false
  }
  if (isEditing.value && form.password && form.password.length < 6) {
    formErrors.password = '密码至少 6 位'
    ok = false
  }
  if (!form.role) {
    formErrors.role = '请选择角色'
    ok = false
  }
  return ok
}

function validateResetForm() {
  Object.keys(resetFormErrors).forEach((k) => delete resetFormErrors[k])
  let ok = true
  if (!resetFormData.password || resetFormData.password.length < 6) {
    resetFormErrors.password = '密码至少 6 位'
    ok = false
  }
  return ok
}

async function submitForm() {
  if (!validateForm()) return
  error.value = ''
  message.value = ''

  const payload = {
    username: form.username.trim(),
    full_name: form.full_name.trim() || null,
    role: form.role,
    is_active: form.is_active,
  }
  if (form.password) {
    payload.password = form.password
  }

  try {
    if (isEditing.value) {
      const res = await fetchApi(`/api/admin/users/${editingUserId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || '保存失败')
      }
      message.value = '用户信息已更新'
    } else {
      const res = await fetchApi('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || '创建失败')
      }
      message.value = '用户已创建'
    }
    showModal.value = false
    await fetchUsers()
  } catch (e) {
    error.value = e.message || '操作失败'
  }
}

async function submitReset() {
  if (!validateResetForm()) return
  error.value = ''
  message.value = ''

  try {
    const res = await fetchApi(`/api/admin/users/${resettingUser.value.id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: resetFormData.password }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '重置失败')
    }
    message.value = `${resettingUser.value.username} 的密码已重置`
    showResetModal.value = false
    await fetchUsers()
  } catch (e) {
    error.value = e.message || '重置失败'
  }
}

async function fetchUsers() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetchApi('/api/admin/users')
    if (!res.ok) throw new Error('加载失败')
    users.value = await res.json()
  } catch (e) {
    error.value = '加载用户列表失败'
  } finally {
    loading.value = false
  }
}

async function deleteUser(user) {
  if (user.id === auth.userId) {
    error.value = '不能删除当前登录账号'
    return
  }
  if (!confirm(`确定删除用户“${user.username}”吗？此操作不可恢复。`)) return

  error.value = ''
  message.value = ''
  try {
    const res = await fetchApi(`/api/admin/users/${user.id}`, { method: 'DELETE' })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || '删除失败')
    }
    message.value = '用户已删除'
    await fetchUsers()
  } catch (e) {
    error.value = e.message || '删除失败'
  }
}

onMounted(fetchUsers)

const sortedUsers = computed(() => {
  return [...users.value].sort((a, b) => a.username.localeCompare(b.username, 'zh-CN'))
})

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

const isSelf = (user) => user.id === auth.userId
</script>

<template>
  <div class="p-6 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">用户管理</h1>
      <button type="button" class="btn-primary" @click="openCreate">+ 新增用户</button>
    </div>

    <div v-if="message" class="mb-4 p-4 rounded-xl bg-green-50 text-green-700 border border-green-200">{{ message }}</div>
    <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 text-red-600 border border-red-200">{{ error }}</div>

    <div v-if="loading" class="text-center py-20 text-muted">加载中...</div>
    <div v-else-if="users.length === 0" class="text-center py-20 text-muted">暂无用户</div>

    <div v-else class="card overflow-hidden">
      <table class="w-full text-left text-sm">
        <thead class="bg-surface-soft">
          <tr class="border-b border-hairline">
            <th class="px-5 py-3 font-semibold">用户名</th>
            <th class="px-5 py-3 font-semibold">姓名</th>
            <th class="px-5 py-3 font-semibold">角色</th>
            <th class="px-5 py-3 font-semibold">状态</th>
            <th class="px-5 py-3 font-semibold">最后登录</th>
            <th class="px-5 py-3 font-semibold text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="user in sortedUsers"
            :key="user.id"
            class="border-b border-hairline last:border-b-0 hover:bg-surface-soft"
          >
            <td class="px-5 py-4 font-medium">{{ user.username }}</td>
            <td class="px-5 py-4">{{ user.full_name || '-' }}</td>
            <td class="px-5 py-4">{{ roleOptions.find((o) => o.value === user.role)?.label || user.role }}</td>
            <td class="px-5 py-4">
              <span
                class="text-xs px-2 py-1 rounded-full border"
                :class="user.is_active ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200'"
              >
                {{ user.is_active ? '启用' : '停用' }}
              </span>
            </td>
            <td class="px-5 py-4">{{ formatDate(user.last_login_at) }}</td>
            <td class="px-5 py-4 text-right">
              <button type="button" class="text-brand hover:underline mr-3" @click="openEdit(user)">编辑</button>
              <button type="button" class="text-brand hover:underline mr-3" @click="openReset(user)">重置密码</button>
              <button
                type="button"
                class="text-up hover:underline"
                :disabled="isSelf(user)"
                :class="isSelf(user) ? 'opacity-50 cursor-not-allowed' : ''"
                @click="deleteUser(user)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-canvas rounded-3xl border border-hairline w-full max-w-md p-6">
        <h2 class="text-xl font-bold mb-6">{{ isEditing ? '编辑用户' : '新增用户' }}</h2>

        <form class="space-y-4" @submit.prevent="submitForm">
          <div>
            <label class="block text-sm font-medium mb-1">用户名 *</label>
            <input v-model="form.username" type="text" class="input w-full" :disabled="isEditing" placeholder="例如：sales01" />
            <p v-if="formErrors.username" class="text-up text-xs mt-1">{{ formErrors.username }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">姓名</label>
            <input v-model="form.full_name" type="text" class="input w-full" placeholder="例如：销售一号" />
          </div>

          <div v-if="!isEditing || form.password !== undefined">
            <label class="block text-sm font-medium mb-1">
              {{ isEditing ? '新密码（留空则不修改）' : '密码 *' }}
            </label>
            <input v-model="form.password" type="password" class="input w-full" placeholder="至少 6 位" />
            <p v-if="formErrors.password" class="text-up text-xs mt-1">{{ formErrors.password }}</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-1">角色 *</label>
            <select v-model="form.role" class="input w-full">
              <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </select>
            <p v-if="formErrors.role" class="text-up text-xs mt-1">{{ formErrors.role }}</p>
          </div>

          <div class="flex items-center gap-2">
            <input id="is_active" v-model="form.is_active" type="checkbox" class="w-4 h-4 accent-brand" />
            <label for="is_active" class="text-sm">启用</label>
          </div>
          <p v-if="isEditing && isSelf({ id: editingUserId })" class="text-up text-xs">不能停用或修改自己的角色</p>

          <div class="flex justify-end gap-3 pt-4">
            <button type="button" class="btn-secondary" @click="closeModal">取消</button>
            <button type="submit" class="btn-primary">{{ isEditing ? '保存' : '创建' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Reset Password Modal -->
    <div
      v-if="showResetModal"
      class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
      @click.self="closeResetModal"
    >
      <div class="bg-canvas rounded-3xl border border-hairline w-full max-w-md p-6">
        <h2 class="text-xl font-bold mb-6">重置密码：{{ resettingUser?.username }}</h2>

        <form class="space-y-4" @submit.prevent="submitReset">
          <div>
            <label class="block text-sm font-medium mb-1">新密码 *</label>
            <input v-model="resetFormData.password" type="password" class="input w-full" placeholder="至少 6 位" />
            <p v-if="resetFormErrors.password" class="text-up text-xs mt-1">{{ resetFormErrors.password }}</p>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <button type="button" class="btn-secondary" @click="closeResetModal">取消</button>
            <button type="submit" class="btn-primary">重置</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
