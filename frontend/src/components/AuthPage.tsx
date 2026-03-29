import { useEffect, useState } from 'react'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(8)

  useEffect(() => {
    if (!loading) {
      setLoadingProgress(8)
      return
    }
    const timer = window.setInterval(() => {
      setLoadingProgress(prev => {
        if (prev >= 90) return prev
        if (prev < 50) return prev + 10
        if (prev < 75) return prev + 5
        return prev + 2
      })
    }, 120)
    return () => window.clearInterval(timer)
  }, [loading])

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
    } catch (err: unknown) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail
        if (typeof detail === 'string') {
          setError(detail)
        } else {
          setError(`Could not reach auth server (${API}). Check frontend env or backend container.`)
        }
      } else {
        setError('Something went wrong')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-6 py-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_20%,rgba(34,211,238,0.2),transparent_35%),radial-gradient(circle_at_80%_0%,rgba(56,189,248,0.15),transparent_45%),linear-gradient(180deg,rgba(15,23,42,0.95)_0%,rgba(2,6,23,1)_65%)]" />
      <div className="relative w-full max-w-md space-y-6 rounded-2xl border border-white/10 bg-slate-900/80 p-8 shadow-2xl backdrop-blur-xl">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-cyan-200/70">LitLens</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-100">Research Workspace</h1>
          <p className="mt-1 text-sm text-slate-400">
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
              className="w-full rounded-lg border border-white/15 bg-slate-900/90 px-4 py-2 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            className="w-full rounded-lg border border-white/15 bg-slate-900/90 px-4 py-2 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            className="w-full rounded-lg border border-white/15 bg-slate-900/90 px-4 py-2 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
          />

          {error && <p className="rounded-lg border border-rose-300/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg border border-cyan-300/40 bg-cyan-500/20 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-500/30 disabled:opacity-50"
          >
            {loading ? '...' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>

          {loading && (
            <div className="mx-auto w-full max-w-xs space-y-1">
              <div className="h-1.5 w-full overflow-hidden rounded-full border border-white/10 bg-slate-800/90">
                <div
                  className="h-full rounded-full bg-cyan-300 transition-[width] duration-150"
                  style={{ width: `${loadingProgress}%` }}
                />
              </div>
              <p className="text-center text-[10px] text-slate-400">Signing you in…</p>
            </div>
          )}
        </form>

        <p className="text-center text-xs text-slate-400">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="text-cyan-300 transition hover:text-cyan-200 hover:underline"
          >
            {mode === 'login' ? 'Register' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
