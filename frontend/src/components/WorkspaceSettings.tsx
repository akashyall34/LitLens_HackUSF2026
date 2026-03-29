import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { api, getUser } from '../lib/auth'

type MemberRow = { user_id: string; email: string; role: string }

export default function WorkspaceSettings({
  open,
  onClose,
  workspaceId,
}: {
  open: boolean
  onClose: () => void
  workspaceId: string
}) {
  const [email, setEmail] = useState('')
  const [inviteStatus, setInviteStatus] = useState(null as any)
  const [loading, setLoading] = useState(false)
  const [team, setTeam] = useState(null as { owner_id: string; members: MemberRow[] } | null)
  const [teamErr, setTeamErr] = useState<string | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setTeamErr(null)
    api
      .get<{ owner_id: string; members: MemberRow[] }>(`/workspaces/${workspaceId}/members`)
      .then(({ data }) => setTeam(data))
      .catch(() => setTeamErr('Could not load members.'))
  }, [open, workspaceId])

  const handleInvite = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setInviteStatus(null)

    try {
      const { data } = await api.post(`/workspaces/${workspaceId}/invite`, { email })
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

  const me = getUser()
  const iAmOwner = me && team && String(me.id) === String(team.owner_id)

  const removeMember = async (userId: string) => {
    if (!window.confirm('Remove this person from the workspace?')) return
    setRemovingId(userId)
    setTeamErr(null)
    try {
      await api.delete(`/workspaces/${workspaceId}/members/${userId}`)
      const { data } = await api.get<{ owner_id: string; members: MemberRow[] }>(
        `/workspaces/${workspaceId}/members`,
      )
      setTeam(data)
    } catch (err: unknown) {
      const d = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setTeamErr(typeof d === 'string' ? d : 'Remove failed.')
    } finally {
      setRemovingId(null)
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
              <p className="text-slate-400 text-xs font-medium mb-2">Members</p>
              {teamErr && <p className="text-red-400 text-xs mb-2">{teamErr}</p>}
              {team && (
                <ul className="space-y-2 mb-4 max-h-40 overflow-y-auto">
                  {team.members.map(m => (
                    <li
                      key={m.user_id}
                      className="flex items-center justify-between gap-2 text-xs text-slate-300"
                    >
                      <span className="truncate">
                        {m.email}
                        {String(m.user_id) === String(team.owner_id) && (
                          <span className="text-slate-500 ml-1">(owner)</span>
                        )}
                      </span>
                      {iAmOwner && String(m.user_id) !== String(team.owner_id) && (
                        <button
                          type="button"
                          disabled={removingId !== null}
                          onClick={() => removeMember(m.user_id)}
                          className="shrink-0 text-red-400 hover:text-red-300 disabled:opacity-40"
                        >
                          {removingId === m.user_id ? '…' : 'Remove'}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {!iAmOwner && team && (
                <p className="text-slate-500 text-[10px] mb-3">
                  Only the workspace owner can remove members.
                </p>
              )}
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
