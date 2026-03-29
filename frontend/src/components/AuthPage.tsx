import { useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const payload = mode === 'login'
        ? { email: form.email, password: form.password }
        : { email: form.email, password: form.password, full_name: form.full_name }

      const { data } = await axios.post(`${API}${endpoint}`, payload)

      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      localStorage.setItem('user', JSON.stringify(data.user))

      onAuth(data.user)
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="bg-slate-800 rounded-xl p-8 w-96 space-y-6">
        <div>
          <h1 className="text-white text-2xl font-bold">LitLens</h1>
          <p className="text-slate-400 text-sm mt-1">
            {mode === 'login' ? 'Sign in to your account' : 'Create an account'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <input
              type="text"
              placeholder="Full name"
              value={form.full_name}
              onChange={e => setForm({ ...form, full_name: e.target.value })}
              className="w-full bg-slate-700 text-white text-sm px-4 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            className="w-full bg-slate-700 text-white text-sm px-4 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            className="w-full bg-slate-700 text-white text-sm px-4 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
          />

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-white text-sm py-2 rounded-lg font-medium"
          >
            {loading ? '...' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p className="text-slate-400 text-xs text-center">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="text-teal-400 hover:underline"
          >
            {mode === 'login' ? 'Register' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
