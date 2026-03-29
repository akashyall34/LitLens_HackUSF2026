import { useState, useRef, useEffect, type FormEvent } from 'react'
import axios from 'axios'
import { ChevronsDown, ChevronsUp } from 'lucide-react'
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

/** Keep follow-up payloads small for reverse proxies and the model context. */
const RAG_HISTORY_MAX_TURNS = 10
const RAG_HISTORY_MAX_QUERY_LEN = 2000
const RAG_HISTORY_MAX_ANSWER_LEN = 1200

function clipRagHistory(turns: ChatTurn[]): { query: string; answer: string }[] {
  return turns
    .filter(t => !t.failed)
    .slice(-RAG_HISTORY_MAX_TURNS)
    .map(t => {
      let query = String(t.query ?? '')
      let answer = String(t.answer ?? '')
      if (query.length > RAG_HISTORY_MAX_QUERY_LEN) {
        query = `${query.slice(0, RAG_HISTORY_MAX_QUERY_LEN - 1)}…`
      }
      if (answer.length > RAG_HISTORY_MAX_ANSWER_LEN) {
        answer = `${answer.slice(0, RAG_HISTORY_MAX_ANSWER_LEN - 1)}…`
      }
      return { query, answer }
    })
}

function describeRagError(e: unknown): string {
  if (!axios.isAxiosError(e)) {
    return e instanceof Error ? e.message : 'Unknown error.'
  }

  const status = e.response?.status
  const raw = e.response?.data

  const fromDetail = (d: unknown): string => {
    if (d == null) return ''
    if (typeof d === 'string') return d
    if (Array.isArray(d)) {
      return d
        .map((x: { msg?: string }) => x?.msg)
        .filter(Boolean)
        .join('; ')
    }
    return ''
  }

  let detail = ''
  if (raw && typeof raw === 'object' && 'detail' in raw) {
    detail = fromDetail((raw as { detail: unknown }).detail)
  }
  if (!detail && typeof raw === 'string') {
    const t = raw.trim()
    if (t && !t.startsWith('<') && t.length < 600) {
      detail = t.slice(0, 400)
    }
  }

  if (detail) return detail
  if (status === 429) return 'Rate limit (try again later).'
  if (status === 401 || status === 403) return 'Session expired — sign in again.'
  if (status === 413) return 'Request too large — tap Clear and start a shorter thread.'
  if (status === 502 || status === 503) return 'API or model unavailable (HTTP ' + status + ').'
  if (status != null) return 'HTTP ' + status + ' from server.'

  const msg = e.message || ''
  if (msg === 'Network Error') {
    return 'Network error (offline, CORS, or API URL mismatch).'
  }
  if (e.code === 'ECONNABORTED') {
    return 'Request timed out — try a shorter question or Clear.'
  }
  return msg || 'No response from server.'
}

export default function RAGQueryBox({ workspaceId }: { workspaceId: string }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [isOpen, setIsOpen] = useState(true)
  const [dragDeltaY, setDragDeltaY] = useState(0)
  const [sheetHeight, setSheetHeight] = useState(380)
  const scrollRef = useRef<HTMLDivElement>(null)
  const sheetRef = useRef<HTMLDivElement>(null)
  const dragStartY = useRef<number | null>(null)
  const dragStartOffset = useRef(0)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [turns, loading])

  useEffect(() => {
    const el = sheetRef.current
    if (!el) return

    const updateHeight = () => setSheetHeight(el.offsetHeight)
    updateHeight()

    if (typeof ResizeObserver !== 'undefined') {
      const obs = new ResizeObserver(updateHeight)
      obs.observe(el)
      return () => obs.disconnect()
    }

    window.addEventListener('resize', updateHeight)
    return () => window.removeEventListener('resize', updateHeight)
  }, [turns.length, loading, isOpen])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || loading) return

    setQuery('')
    setLoading(true)

    const id = crypto.randomUUID()

    const history = clipRagHistory(turns)

    try {
      const { data } = await api.post<{
        answer: string
        sources?: Source[]
        vector_search_ms?: number
        llm_ms?: number
      }>(
        '/rag/query',
        { query: q, workspace_id: workspaceId, history },
        { timeout: 120_000 },
      )

      setTurns(prev => [
        ...prev,
        {
          id,
          query: q,
          answer: String(data.answer ?? '').trim() || '(Empty reply.)',
          sources: data.sources || [],
          vector_search_ms: data.vector_search_ms,
          llm_ms: data.llm_ms,
        },
      ])
    } catch (e: unknown) {
      if (import.meta.env.DEV) {
        const ax = axios.isAxiosError(e) ? e : null
        console.warn('[RAG]', ax?.response?.status, ax?.message, ax?.response?.data)
      }
      const reason = describeRagError(e)
      setTurns(prev => [
        ...prev,
        {
          id,
          query: q,
          answer: `Could not get an answer: ${reason}`,
          sources: [],
          failed: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const revealHeight = 46
  const closedOffset = Math.max(0, sheetHeight - revealHeight)
  const restingOffset = isOpen ? 0 : closedOffset
  const translateY = Math.min(closedOffset, Math.max(0, restingOffset + dragDeltaY))

  const onHandlePointerDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    dragStartY.current = e.clientY
    dragStartOffset.current = restingOffset
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const onHandlePointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (dragStartY.current == null) return
    const rawOffset = dragStartOffset.current + (e.clientY - dragStartY.current)
    const clampedOffset = Math.min(closedOffset, Math.max(0, rawOffset))
    setDragDeltaY(clampedOffset - restingOffset)
  }

  const onHandlePointerUp = () => {
    if (dragStartY.current == null) return
    const finalOffset = Math.min(closedOffset, Math.max(0, restingOffset + dragDeltaY))
    const shouldClose = finalOffset > closedOffset * 0.45
    setIsOpen(!shouldClose)
    setDragDeltaY(0)
    dragStartY.current = null
  }

  return (
    <div
      ref={sheetRef}
      className="absolute bottom-4 left-1/2 z-20 flex max-h-[min(56vh,460px)] w-[min(680px,calc(100vw-2rem))] flex-col gap-2 rounded-2xl border border-white/10 bg-slate-900/80 p-2 shadow-2xl backdrop-blur-xl"
      style={{
        transform: `translate(-50%, ${translateY}px)`,
        transition: dragStartY.current == null ? 'transform 180ms ease-out' : 'none',
      }}
    >
      <button
        type="button"
        aria-label={isOpen ? 'Collapse chat' : 'Expand chat'}
        onClick={() => {
          setIsOpen(o => !o)
          setDragDeltaY(0)
        }}
        onPointerDown={onHandlePointerDown}
        onPointerMove={onHandlePointerMove}
        onPointerUp={onHandlePointerUp}
        onPointerCancel={onHandlePointerUp}
        className="mx-auto inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/15 bg-slate-800/85 text-slate-200 transition hover:bg-slate-700/90"
      >
        {isOpen ? <ChevronsDown size={16} /> : <ChevronsUp size={16} />}
      </button>

      <div
        ref={scrollRef}
        className="flex min-h-0 flex-col gap-3 overflow-y-auto overflow-x-hidden rounded-xl border border-white/10 bg-slate-900/70 p-4"
      >
        {turns.length === 0 && !loading && (
          <p className="px-2 py-6 text-center text-xs text-slate-400">
            Ask about your workspace papers. Follow-up questions use this thread as context; retrieval still uses
            your latest message to find relevant papers.
          </p>
        )}

        {turns.map(t => (
          <div key={t.id} className="space-y-2 shrink-0">
            <div className="flex justify-end">
              <div className="max-w-[90%] rounded-xl border border-cyan-300/30 bg-cyan-500/20 px-3 py-2 text-right">
                <p className="text-white text-sm leading-snug whitespace-pre-wrap break-words">{t.query}</p>
              </div>
            </div>
            <div className="flex justify-start">
              <div
                className={`max-w-[95%] rounded-xl border px-3 py-2 space-y-2 ${
                  t.failed ? 'border-red-500/40 bg-rose-500/10' : 'border-white/10 bg-slate-950/60'
                }`}
              >
                <p className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {t.answer}
                </p>
                {t.sources.length > 0 && (
                  <div className="space-y-1 border-t border-white/10 pt-2">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-cyan-200/75">Sources</p>
                    {t.sources.map(s => (
                      <p key={`${t.id}-${s.paper_id}`} className="text-xs text-slate-300">
                        · {s.title} ({Math.round(s.score * 100)}% match)
                      </p>
                    ))}
                  </div>
                )}
                {!t.failed && (t.vector_search_ms != null || t.llm_ms != null) && (
                  <p className="text-[10px] text-slate-500">
                    Vector: {t.vector_search_ms ?? '—'}ms · LLM: {t.llm_ms ?? '—'}ms
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start shrink-0">
            <div className="rounded-xl border border-white/10 bg-slate-950/60 px-3 py-2">
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
          className="flex-1 rounded-xl border border-white/15 bg-slate-900/85 px-4 py-2 text-sm text-white focus:border-cyan-300/60 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="shrink-0 rounded-xl border border-cyan-300/40 bg-cyan-500/20 px-4 py-2 text-sm font-medium text-cyan-100 transition hover:bg-cyan-500/30 disabled:opacity-50"
        >
          {loading ? '…' : 'Send'}
        </button>
        {turns.length > 0 && (
          <button
            type="button"
            onClick={() => setTurns([])}
            className="shrink-0 rounded-xl border border-white/15 px-2 py-2 text-xs text-slate-300 transition hover:bg-slate-800/70 hover:text-slate-100"
          >
            Clear
          </button>
        )}
      </form>
    </div>
  )
}
