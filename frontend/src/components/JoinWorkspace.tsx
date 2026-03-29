import { useEffect, useRef, useState } from 'react'
import { api, getUser } from '../lib/auth'
import AuthPage from './AuthPage'

export default function JoinWorkspace() {
  const [user, setUser] = useState(getUser)
  const token = new URLSearchParams(window.location.search).get('token')
  const [status, setStatus] = useState<'idle' | 'ok' | 'err'>('idle')
  const [message, setMessage] = useState('')
  const attempted = useRef(false)

  useEffect(() => {
    if (!user || !token || attempted.current) return
    attempted.current = true
    ;(async () => {
      try {
        await api.post('/workspaces/join', { token })
        setStatus('ok')
        setMessage('You have joined the workspace. Redirecting…')
        window.setTimeout(() => {
          window.location.replace('/')
        }, 1200)
      } catch (err: any) {
        setStatus('err')
        const d = err.response?.data?.detail
        setMessage(typeof d === 'string' ? d : 'Could not accept this invite.')
      }
    })()
  }, [user, token])

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-300 text-sm px-4">
        This invite link is missing a token. Ask your teammate to send a new invite.
      </div>
    )
  }

  if (!user) {
    return (
      <div>
        <p className="fixed top-4 left-0 right-0 text-center text-slate-400 text-xs z-20 px-4">
          Sign in with the email that received the invite, then you will be added automatically.
        </p>
        <AuthPage onAuth={setUser} />
      </div>
    )
  }

  if (status === 'ok') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-teal-300 text-sm">
        {message}
      </div>
    )
  }

  if (status === 'err') {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center gap-4 text-sm px-6 max-w-md mx-auto text-center">
        <p className="text-red-300">{message}</p>
        <a href="/" className="text-teal-400 hover:underline">
          Back to LitLens
        </a>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400 text-sm">
      Joining workspace…
    </div>
  )
}
