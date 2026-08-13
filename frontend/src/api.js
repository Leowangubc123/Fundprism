const baseUrl = import.meta.env.VITE_API_BASE_URL || ''

export function apiUrl(path) {
  if (path.startsWith('/')) {
    return `${baseUrl}${path}`
  }
  return `${baseUrl}/${path}`
}

export function fetchApi(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = localStorage.getItem('token')
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }
  return fetch(apiUrl(path), { ...options, headers })
}
