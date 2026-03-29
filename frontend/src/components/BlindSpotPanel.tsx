import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { api } from '../lib/auth'

const tabs = ['Citation Gaps', 'Conceptual Gaps']

const WORKSPACE_ID = '00000000-0000-0000-0000-000000000001'

type GapsState = {
  citation_gaps: any[]
  semantic_gaps: any[]
  team_coverage?: { member_email: string; papers_added: number }[]
}

export default function BlindSpotPanel({ open, onClose }) {
  const [activeTab, setActiveTab] = useState(0)
  const [gaps, setGaps] = useState<GapsState>({
    citation_gaps: [],
    semantic_gaps: [],
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchGaps = useCallback(async () => {
    const { data } = await api.get<GapsState>(`/gaps/${WORKSPACE_ID}`)
    setGaps({
      citation_gaps: data.citation_gaps || [],
      semantic_gaps: data.semantic_gaps || [],
      team_coverage: data.team_coverage,
    })
  }, [])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchGaps()
      .catch(() => {
        if (!cancelled) setError('Could not load blind spots. Try again.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, fetchGaps])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const runConceptualScan = async () => {
    setScanMessage(null)
    setError(null)
    setScanning(true)
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    try {
      const { data } = await api.post<{ job_id: string }>(`/gaps/${WORKSPACE_ID}/detect`)
      const jobId = data.job_id
      pollRef.current = setInterval(async () => {
        try {
          const st = await api.get<{ status: string; progress: number }>(`/gaps/status/${jobId}`)
          if (st.data.status === 'done') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setScanning(false)
            setScanMessage('Analysis complete.')
            await fetchGaps()
          } else if (st.data.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setScanning(false)
            setError('Conceptual gap job failed. Check server logs and GEMINI_API_KEY.')
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setScanning(false)
          setError('Lost connection while waiting for the job.')
        }
      }, 1500)
    } catch {
      setScanning(false)
      setError('Could not start gap detection.')
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ x: '-100%' }}
          animate={{ x: 0 }}
          exit={{ x: '-100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed top-0 left-0 h-full w-96 bg-slate-800 shadow-2xl z-10 flex flex-col"
        >
          <div className="flex items-center justify-between p-4 border-b border-slate-700">
            <h2 className="text-white font-semibold text-lg">Blind Spots</h2>
            <button type="button" onClick={onClose} className="text-slate-400 hover:text-white">
              <X size={20} />
            </button>
          </div>

          <div className="flex border-b border-slate-700">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(i)}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  activeTab === i
                    ? 'text-teal-400 border-b-2 border-teal-400'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="px-4 py-2 border-b border-slate-700 space-y-2">
            <button
              type="button"
              disabled={scanning}
              onClick={runConceptualScan}
              className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs py-2 rounded-lg font-medium"
            >
              {scanning ? 'Running AI conceptual scan…' : 'Run AI conceptual gap scan'}
            </button>
            <p className="text-slate-500 text-[10px] leading-snug">
              Citation gaps load automatically. Conceptual gaps need this scan (worker + Gemini). Requires
              several cited papers outside your workspace with embeddings.
            </p>
            {scanMessage && <p className="text-teal-400 text-xs">{scanMessage}</p>}
            {error && <p className="text-red-400 text-xs">{error}</p>}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {loading && <p className="text-slate-400 text-xs">Loading…</p>}

            {gaps.team_coverage && gaps.team_coverage.length > 0 && (
              <div className="bg-slate-900/50 rounded-lg p-3 space-y-1">
                <p className="text-slate-400 text-xs font-medium">Team coverage</p>
                {gaps.team_coverage.map(row => (
                  <p key={row.member_email} className="text-slate-500 text-[11px]">
                    {row.member_email}: {row.papers_added} papers added
                  </p>
                ))}
              </div>
            )}

            {activeTab === 0 && !loading && gaps.citation_gaps.length === 0 && (
              <p className="text-slate-400 text-xs leading-relaxed">
                No citation gaps yet. They appear when <strong>two or more</strong> papers in this workspace
                cite the <strong>same</strong> paper that is <strong>not</strong> in the workspace — and that
                relationship exists in the citations table (usually after ingest pulls references).
              </p>
            )}

            {activeTab === 0 &&
              gaps.citation_gaps.map(gap => (
                <div key={gap.paper?.id} className="bg-slate-700 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs bg-red-500 text-white px-2 py-0.5 rounded-full">
                      Cited by {gap.cited_by_count}
                    </span>
                    <span className="text-xs text-slate-400">{gap.paper?.year}</span>
                  </div>
                  <p className="text-white text-sm font-medium">{gap.paper?.title}</p>
                  <p className="text-slate-400 text-xs">
                    {(gap.paper?.authors || []).join(', ')}
                  </p>
                  {gap.why_matters && (
                    <p className="text-slate-300 text-xs leading-relaxed">{gap.why_matters}</p>
                  )}
                  <button type="button" className="text-xs text-teal-400 hover:underline">
                    Add to workspace →
                  </button>
                </div>
              ))}

            {activeTab === 1 && !loading && gaps.semantic_gaps.length === 0 && !scanning && (
              <p className="text-slate-400 text-xs leading-relaxed">
                No conceptual gaps yet. Click <strong>Run AI conceptual gap scan</strong> above. The pipeline
                needs enough cited (but not in workspace) papers with embeddings to form clusters; small
                workspaces may return none until you add more related papers.
              </p>
            )}

            {activeTab === 1 &&
              gaps.semantic_gaps.map((gap, idx) => (
                <div
                  key={gap.label || gap.cluster_label || `gap-${idx}`}
                  className="bg-slate-700 rounded-lg p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs bg-purple-500 text-white px-2 py-0.5 rounded-full">
                      {gap.label || gap.cluster_label || 'Cluster'}
                    </span>
                    <span className="text-xs text-slate-400">
                      {Math.round((gap.coverage_score ?? 0) * 100)}% covered
                    </span>
                  </div>
                  <div className="w-full bg-slate-600 rounded-full h-1.5">
                    <div
                      className="bg-purple-400 h-1.5 rounded-full"
                      style={{ width: `${Math.min(100, (gap.coverage_score ?? 0) * 100)}%` }}
                    />
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">{gap.why_matters}</p>
                  <div className="space-y-1">
                    {(gap.top_papers || []).slice(0, 5).map((p: { id: string; title: string }) => (
                      <p key={p.id} className="text-slate-400 text-xs">
                        · {p.title}
                      </p>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
