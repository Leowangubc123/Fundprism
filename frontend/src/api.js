import { useAuthStore } from './stores/auth'

const baseUrl = import.meta.env.VITE_API_BASE_URL || ''

export function apiUrl(path) {
  if (path.startsWith('/')) {
    return `${baseUrl}${path}`
  }
  return `${baseUrl}/${path}`
}

export async function fetchApi(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = localStorage.getItem('token')
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(apiUrl(path), { ...options, headers })

  if (
    response.status === 401 &&
    !options.skipAuthRedirect &&
    !path.includes('/auth/login')
  ) {
    const auth = useAuthStore()
    auth.logout()
    window.location.href = '/login'
  }

  return response
}
