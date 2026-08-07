<script setup>
import { useAuthStore } from '../../stores/auth'
const auth = useAuthStore()
</script>

<template>
  <div class="min-h-screen bg-surface-soft p-6">
    <h1 class="text-xl font-bold">管理后台</h1>
    <p class="text-muted mt-2">欢迎，{{ auth.username }}</p>
  </div>
</template>
