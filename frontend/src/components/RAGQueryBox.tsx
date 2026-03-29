import { useState, useRef, useEffect, type FormEvent } from 'react'
import { api } from '../lib/auth'

type Source = { paper_id: string; title: string; score: number }

type ChatTurn = {
  id: string
  query: string
  answer: string
  sources: Source[]
  vector_search_ms?: number
  llm_ms?: number
  failed?: boolean
}

export default function RAGQueryBox({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [turns, loading])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || loading) return

    setQuery('')
    setLoading(true)

    const id = crypto.randomUUID()

    try {
      const { data } = await api.post<{
        answer: string
        sources?: Source[]
        vector_search_ms?: number
        llm_ms?: number
      }>('/rag/query', { query: q, workspace_id: workspaceId })

      setTurns(prev => [
        ...prev,
        {
          id,
          query: q,
          answer: data.answer,
          sources: data.sources || [],
          vector_search_ms: data.vector_search_ms,
          llm_ms: data.llm_ms,
        },
      ])
    } catch {
      setTurns(prev => [
        ...prev,
        {
          id,
          query: q,
          answer: 'Request failed. Please try again.',
          sources: [],
          failed: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-[min(600px,calc(100vw-2rem))] z-10 flex flex-col gap-2 max-h-[min(52vh,420px)]">
      <div
        ref={scrollRef}
        className="overflow-y-auto overflow-x-hidden rounded-lg border border-slate-600/80 bg-slate-900/95 shadow-lg backdrop-blur-sm flex flex-col gap-3 p-3 min-h-0"
      >
        {turns.length === 0 && !loading && (
          <p className="text-slate-500 text-xs text-center py-6 px-2">
            Ask about your workspace papers. Each answer stays in the thread so you can scroll back.
          </p>
        )}

        {turns.map(t => (
          <div key={t.id} className="space-y-2 shrink-0">
            <div className="flex justify-end">
              <div className="max-w-[90%] rounded-lg bg-slate-700 px-3 py-2 text-right">
                <p className="text-white text-sm leading-snug whitespace-pre-wrap break-words">{t.query}</p>
              </div>
            </div>
            <div className="flex justify-start">
              <div
                className={`max-w-[95%] rounded-lg border px-3 py-2 space-y-2 ${
                  t.failed ? 'border-red-500/40 bg-slate-800/80' : 'border-slate-600 bg-slate-800/90'
                }`}
              >
                <p className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {t.answer}
                </p>
                {t.sources.length > 0 && (
                  <div className="space-y-1 border-t border-slate-600/60 pt-2">
                    <p className="text-slate-400 text-[10px] font-medium uppercase tracking-wide">Sources</p>
                    {t.sources.map(s => (
                      <p key={`${t.id}-${s.paper_id}`} className="text-slate-400 text-xs">
                        · {s.title} ({Math.round(s.score * 100)}% match)
                      </p>
                    ))}
                  </div>
                )}
                {!t.failed && (t.vector_search_ms != null || t.llm_ms != null) && (
                  <p className="text-slate-600 text-[10px]">
                    Vector: {t.vector_search_ms ?? '—'}ms · LLM: {t.llm_ms ?? '—'}ms
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start shrink-0">
            <div className="rounded-lg border border-slate-600 bg-slate-800/60 px-3 py-2">
              <p className="text-slate-400 text-sm">Thinking…</p>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 shrink-0">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Ask a follow-up about your papers…"
          className="flex-1 bg-slate-800 text-white text-sm px-4 py-2 rounded-lg border border-slate-600 focus:outline-none focus:border-teal-400"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg shrink-0"
        >
          {loading ? '…' : 'Send'}
        </button>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={() => setTurns([])}
            className="text-slate-400 hover:text-white text-xs px-2 py-2 border border-slate-600 rounded-lg shrink-0"
          >
            Clear
          </button>
        )}
      </form>
    </div>
  )
}
