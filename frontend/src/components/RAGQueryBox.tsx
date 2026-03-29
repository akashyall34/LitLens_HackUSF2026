import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/auth'

const WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

export default function RAGQueryBox() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null as any)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setResult(null)

    try {
      const { data } = await api.post('/rag/query', { query, workspace_id: WORKSPACE_ID })
      setResult(data)
    } catch {
      setResult({ answer: 'Request failed. Please try again.', sources: [] })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-[600px] z-10">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask a question about your papers..."
          className="flex-1 bg-slate-800 text-white text-sm px-4 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
        >
          {loading ? '...' : 'Ask'}
        </button>
      </form>

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-2 bg-slate-800 border border-slate-600 rounded-lg p-4 space-y-3"
          >
            <p className="text-white text-sm leading-relaxed">{result.answer}</p>

            {result.sources && result.sources.length > 0 && (
              <div className="space-y-1">
                <p className="text-slate-400 text-xs font-medium">Sources</p>
                {result.sources.map(s => (
                  <p key={s.paper_id} className="text-slate-400 text-xs">
                    · {s.title} ({Math.round(s.score * 100)}% match)
                  </p>
                ))}
              </div>
            )}

            <p className="text-slate-600 text-xs">
              Vector: {result.vector_search_ms}ms · LLM: {result.llm_ms}ms
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
