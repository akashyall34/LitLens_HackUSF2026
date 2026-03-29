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
          className="fixed top-0 right-0 h-full w-96 bg-slate-800 shadow-2xl z-10 p-6 overflow-y-auto"
        >
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white"
          >
            <X size={20} />
          </button>

          <div className="mt-6 space-y-4">
            <h2 className="text-white font-semibold text-lg leading-snug">
              {paper.title ?? 'Paper'}
            </h2>

            <div className="flex gap-4 text-sm text-slate-400">
              <span>{paper.year ?? '—'}</span>
              <span>{paper.citation_count ?? 0} citations</span>
            </div>

            <button
              type="button"
              disabled={removing}
              onClick={handleRemoveFromWorkspace}
              className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 border border-red-500/50 rounded-lg px-3 py-2 w-full justify-center disabled:opacity-40"
            >
              <Trash2 size={16} />
              {removing ? 'Removing…' : 'Remove from workspace'}
            </button>
            {removeErr && <p className="text-red-400 text-xs">{removeErr}</p>}

            {paper.venue && (
              <p className="text-sm text-slate-400 italic">{paper.venue}</p>
            )}

            {paper.abstract && (
              <p className="text-sm text-slate-300 leading-relaxed">
                {paper.abstract}
              </p>
            )}

            {paper.url && typeof paper.url === 'string' && (
              <a
                href={paper.url}
                target="_blank"
                rel="noreferrer"
                className="inline-block text-sm text-teal-400 hover:underline"
              >
                View on Semantic Scholar →
              </a>
            )}

            <div className="pt-4 border-t border-slate-700 space-y-3">
              <p className="text-slate-400 text-xs font-medium">Comments</p>

              {paperComments.map((c, i) => (
                <div key={i} className="space-y-0.5">
                  <p className="text-slate-400 text-xs">{c.author}</p>
                  <p className="text-slate-300 text-xs">{c.content}</p>
                </div>
              ))}

              <form onSubmit={handleComment} className="flex gap-2">
                <input
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  placeholder="Add a comment..."
                  className="flex-1 bg-slate-700 text-white text-xs px-3 py-1.5 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
                />
                <button
                  type="submit"
                  className="bg-teal-500 hover:bg-teal-400 text-white text-xs px-3 py-1.5 rounded-lg"
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
