import axios from 'axios'

const API = import.meta.env.VITE_API_URL

export const api = axios.create({ baseURL: API })

// Attach access token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  res => res,
  async err => {
    if (err.response?.status === 401) {
      const refresh_token = localStorage.getItem('refresh_token')
      if (!refresh_token) { logout(); return Promise.reject(err) }
      try {
        const { data } = await axios.post(`${API}/auth/refresh`, { refresh_token })
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        err.config.headers.Authorization = `Bearer ${data.access_token}`
        return api(err.config)
      } catch {
        logout()
        return Promise.reject(err)
      }
    }
    return Promise.reject(err)
  }
)

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
  window.location.href = '/login'
}

export function getUser() {
  const u = localStorage.getItem('user')
  return u ? JSON.parse(u) : null
}
