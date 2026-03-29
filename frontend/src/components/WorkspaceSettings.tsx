import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { api } from '../lib/auth'

const WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

export default function WorkspaceSettings({ open, onClose }) {
  const [email, setEmail] = useState('')
  const [inviteStatus, setInviteStatus] = useState(null as any)
  const [loading, setLoading] = useState(false)

  const handleInvite = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setInviteStatus(null)

    try {
      const { data } = await api.post(`/workspaces/${WORKSPACE_ID}/invite`, { email })
      setInviteStatus({
        success: true,
        join_url: data.join_url,
        email_sent: data.email_sent,
      })
      setEmail('')
    } catch (err) {
      setInviteStatus({ success: false, message: err.response?.data?.detail || 'Invite failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 z-20 flex items-center justify-center"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={e => e.stopPropagation()}
            className="bg-slate-800 rounded-xl p-6 w-96 space-y-5"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-white font-semibold text-lg">Workspace Settings</h2>
              <button onClick={onClose} className="text-slate-400 hover:text-white">
                <X size={18} />
              </button>
            </div>

            <div>
              <p className="text-slate-400 text-xs mb-3">Invite a collaborator by email</p>
              <form onSubmit={handleInvite} className="flex gap-2">
                <input
                  type="email"
                  placeholder="colleague@university.edu"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="flex-1 bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-white text-sm px-3 py-2 rounded-lg"
                >
                  {loading ? '...' : 'Invite'}
                </button>
              </form>
            </div>

            {inviteStatus && (
              <div className={`rounded-lg p-3 text-sm ${inviteStatus.success ? 'bg-teal-900/40 text-teal-300' : 'bg-red-900/40 text-red-300'}`}>
                {inviteStatus.success ? (
                  <div className="space-y-1">
                    <p>Invite created.</p>
                    {inviteStatus.email_sent === false && (
                      <p className="text-amber-200/90 text-xs">
                        Email could not be sent (check SES setup). Share the link below manually.
                      </p>
                    )}
                    <p className="text-xs text-slate-400 break-all">{inviteStatus.join_url}</p>
                  </div>
                ) : (
                  <p>{inviteStatus.message}</p>
                )}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
