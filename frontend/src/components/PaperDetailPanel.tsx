import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { comments } from '../lib/collaboration'

export default function PaperDetailPanel({ paper, onClose }) {
  const [commentText, setCommentText] = useState('')
  const [paperComments, setPaperComments] = useState([] as any[])

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
              {paper.title}
            </h2>

            <div className="flex gap-4 text-sm text-slate-400">
              <span>{paper.year}</span>
              <span>{paper.citation_count} citations</span>
            </div>

            {paper.venue && (
              <p className="text-sm text-slate-400 italic">{paper.venue}</p>
            )}

            {paper.abstract && (
              <p className="text-sm text-slate-300 leading-relaxed">
                {paper.abstract}
              </p>
            )}

            {paper.url && (
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
