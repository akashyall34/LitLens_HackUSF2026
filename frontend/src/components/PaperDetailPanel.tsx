import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trash2, X } from 'lucide-react'
import { comments } from '../lib/collaboration'
import { api } from '../lib/auth'

type GraphPaper = {
  id: string
  title?: string
  year?: number
  citation_count?: number
  venue?: string
  abstract?: string
  url?: string
}

type Props = {
  paper: GraphPaper | null
  onClose: () => void
  workspaceId: string
  onRemovedFromWorkspace?: () => void
}

export default function PaperDetailPanel({
  paper,
  onClose,
  workspaceId,
  onRemovedFromWorkspace,
}: Props) {
  const [commentText, setCommentText] = useState('')
  const [paperComments, setPaperComments] = useState([] as any[])
  const [removing, setRemoving] = useState(false)
  const [removeErr, setRemoveErr] = useState<string | null>(null)

  useEffect(() => {
    const update = () => {
      setPaperComments(
        (comments.toArray() as any[]).filter(c => c.paper_id === paper?.id)
      )
    }
    update()
    comments.observe(update)
    return () => comments.unobserve(update)
  }, [paper?.id])

  const handleComment = (e) => {
    e.preventDefault()
    if (!commentText.trim() || !paper) return
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    comments.push([{
      paper_id: paper.id,
      author: user.email,
      content: commentText,
      created_at: new Date().toISOString(),
    }])
    setCommentText('')
  }

  const handleRemoveFromWorkspace = async () => {
    if (!paper?.id) return
    if (
      !window.confirm(
        'Remove this paper from the workspace? The graph will update; you can add it again later.',
      )
    ) {
      return
    }
    setRemoving(true)
    setRemoveErr(null)
    try {
      await api.delete(`/workspaces/${workspaceId}/papers/${paper.id}`)
      onRemovedFromWorkspace?.()
      onClose()
    } catch (e: unknown) {
      const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setRemoveErr(typeof d === 'string' ? d : 'Could not remove paper.')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <AnimatePresence>
      {paper && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed right-4 top-24 z-20 h-[calc(100vh-7rem)] w-[24rem] overflow-y-auto rounded-2xl border border-white/10 bg-slate-900/85 p-6 shadow-2xl backdrop-blur-xl"
        >
          <button
            onClick={onClose}
            className="absolute right-4 top-4 text-slate-400 transition hover:text-slate-100"
          >
            <X size={20} />
          </button>

          <div className="mt-6 space-y-4">
            <p className="text-[10px] uppercase tracking-[0.16em] text-cyan-200/70">Paper Details</p>
            <h2 className="text-lg font-semibold leading-snug text-slate-100">
              {paper.title ?? 'Paper'}
            </h2>

            <div className="flex gap-4 text-sm text-slate-300">
              <span>{paper.year ?? '—'}</span>
              <span>{paper.citation_count ?? 0} citations</span>
            </div>

            <button
              type="button"
              disabled={removing}
              onClick={handleRemoveFromWorkspace}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-rose-300/40 bg-rose-500/15 px-3 py-2 text-sm text-rose-200 transition hover:bg-rose-500/25 disabled:opacity-40"
            >
              <Trash2 size={16} />
              {removing ? 'Removing…' : 'Remove from workspace'}
            </button>
            {removeErr && <p className="text-red-400 text-xs">{removeErr}</p>}

            {paper.venue && (
              <p className="text-sm italic text-slate-400">{paper.venue}</p>
            )}

            {paper.abstract && (
              <p className="rounded-xl border border-white/10 bg-slate-950/45 p-3 text-sm leading-relaxed text-slate-300">
                {paper.abstract}
              </p>
            )}

            {paper.url && typeof paper.url === 'string' && (
              <a
                href={paper.url}
                target="_blank"
                rel="noreferrer"
                className="inline-block text-sm text-cyan-300 transition hover:text-cyan-200 hover:underline"
              >
                View on Semantic Scholar →
              </a>
            )}

            <div className="space-y-3 border-t border-white/10 pt-4">
              <p className="text-xs font-medium text-slate-300">Comments</p>

              {paperComments.map((c, i) => (
                <div key={i} className="space-y-0.5 rounded-lg border border-white/10 bg-slate-950/50 px-2 py-1.5">
                  <p className="text-xs text-slate-400">{c.author}</p>
                  <p className="text-xs text-slate-200">{c.content}</p>
                </div>
              ))}

              <form onSubmit={handleComment} className="flex gap-2">
                <input
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  placeholder="Add a comment..."
                  className="flex-1 rounded-lg border border-white/15 bg-slate-900/90 px-3 py-1.5 text-xs text-white focus:border-cyan-300/60 focus:outline-none"
                />
                <button
                  type="submit"
                  className="rounded-lg border border-cyan-300/40 bg-cyan-500/20 px-3 py-1.5 text-xs text-cyan-100 transition hover:bg-cyan-500/30"
                >
                  Post
                </button>
              </form>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
