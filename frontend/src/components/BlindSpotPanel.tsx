import { useCallback, useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { api } from '../lib/auth'
import { waitIngestDone } from '../lib/waitIngestDone'

const tabs = ['Citation Gaps', 'Conceptual Gaps']

type GapsState = {
  citation_gaps: any[]
  semantic_gaps: any[]
  team_coverage?: { member_email: string; papers_added: number }[]
}

type Props = {
  open: boolean
  onClose: () => void
  workspaceId: string
  /** Refetch graph after a gap paper is ingested into the workspace */
  onWorkspacePapersChanged?: () => void
}

export default function BlindSpotPanel({
  open,
  onClose,
  workspaceId,
  onWorkspacePapersChanged,
}: Props) {
  const [activeTab, setActiveTab] = useState(0)
  const [gaps, setGaps] = useState<GapsState>({
    citation_gaps: [],
    semantic_gaps: [],
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)
  const [addingPaperId, setAddingPaperId] = useState<string | null>(null)
  const [citationRefreshing, setCitationRefreshing] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchGaps = useCallback(async () => {
    const { data } = await api.get<GapsState>(`/gaps/${workspaceId}`)
    setGaps({
      citation_gaps: data.citation_gaps || [],
      semantic_gaps: data.semantic_gaps || [],
      team_coverage: data.team_coverage,
    })
  }, [workspaceId])

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

  const refreshCitationGaps = async () => {
    setError(null)
    setCitationRefreshing(true)
    try {
      await fetchGaps()
    } catch {
      setError('Could not refresh citation gaps.')
    } finally {
      setCitationRefreshing(false)
    }
  }

  const runConceptualScan = async () => {
    setScanMessage(null)
    setError(null)
    setScanning(true)
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    try {
      const { data } = await api.post<{ job_id: string }>(`/gaps/${workspaceId}/detect`)
      const jobId = data.job_id
      pollRef.current = setInterval(async () => {
        try {
          const st = await api.get<{ status: string; progress: number }>(`/gaps/status/${jobId}`)
          if (st.data.status === 'done') {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            setScanning(false)
            const fresh = await api.get<GapsState>(`/gaps/${workspaceId}`)
            const sem = fresh.data.semantic_gaps || []
            setGaps({
              citation_gaps: fresh.data.citation_gaps || [],
              semantic_gaps: sem,
              team_coverage: fresh.data.team_coverage,
            })
            setScanMessage(
              sem.length > 0
                ? 'Analysis complete.'
                : 'Analysis complete. No new conceptual clusters (previous results kept if available).',
            )
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
          className="fixed left-4 top-24 z-20 flex h-[calc(100vh-7rem)] w-[24rem] flex-col overflow-hidden rounded-2xl border border-white/10 bg-slate-900/85 shadow-2xl backdrop-blur-xl"
        >
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div>
              <h2 className="text-base font-semibold text-slate-100">Blind Spots</h2>
              <p className="text-[10px] uppercase tracking-[0.16em] text-cyan-200/70">Coverage Analysis</p>
            </div>
            <button type="button" onClick={onClose} className="text-slate-400 transition hover:text-slate-100">
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-2 border-b border-white/10 px-2 py-2">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                type="button"
                onClick={() => {
                  setActiveTab(i)
                  setError(null)
                  if (i === 0) setScanMessage(null)
                }}
                className={`rounded-lg px-2 py-2 text-xs font-medium transition ${
                  activeTab === i
                    ? 'bg-cyan-500/20 text-cyan-100 ring-1 ring-cyan-300/40'
                    : 'text-slate-400 hover:bg-slate-800/80 hover:text-slate-100'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="space-y-2 border-b border-white/10 px-4 py-3">
            {activeTab === 0 ? (
              <>
                <button
                  type="button"
                  disabled={citationRefreshing || loading}
                  onClick={refreshCitationGaps}
                  className="w-full rounded-lg border border-cyan-300/40 bg-cyan-500/20 py-2 text-xs font-semibold text-cyan-100 transition hover:bg-cyan-500/30 disabled:opacity-50"
                >
                  {citationRefreshing ? 'Refreshing…' : 'Refresh citation gaps'}
                </button>
                <p className="text-[10px] leading-snug text-slate-400">
                  Citation gaps are derived from the citations already in your workspace (usually after ingest
                  pulls references). They show when two or more workspace papers cite the same paper that is{' '}
                  <strong>not</strong> in the workspace. Use refresh after adding papers—no AI on this tab.
                </p>
              </>
            ) : (
              <>
                <button
                  type="button"
                  disabled={scanning}
                  onClick={runConceptualScan}
                  className="w-full rounded-lg border border-indigo-300/40 bg-indigo-500/20 py-2 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-50"
                >
                  {scanning ? 'Running AI conceptual scan…' : 'Run AI conceptual gap scan'}
                </button>
                <p className="text-[10px] leading-snug text-slate-400">
                  Primary signal: papers your workspace cites that are <strong>not</strong> in the workspace
                  (clustered + labeled with Gemini). If everything cited is already inside, you still get a{' '}
                  <strong>workspace summary</strong> from how your papers relate in embedding space (2+ papers
                  with embeddings). Re-running keeps prior Redis results if a run returns nothing.
                </p>
                {scanMessage && <p className="text-xs text-cyan-300">{scanMessage}</p>}
              </>
            )}
            {error && <p className="text-red-400 text-xs">{error}</p>}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {loading && <p className="text-slate-400 text-xs">Loading…</p>}

            {gaps.team_coverage && gaps.team_coverage.length > 0 && (
              <div className="space-y-1 rounded-xl border border-white/10 bg-slate-950/50 p-3">
                <p className="text-xs font-medium text-slate-300">Team coverage</p>
                {gaps.team_coverage.map(row => (
                  <p key={row.member_email} className="text-[11px] text-slate-400">
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
                <div key={gap.paper?.id} className="space-y-2 rounded-xl border border-white/10 bg-slate-950/55 p-4">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-rose-500/85 px-2 py-0.5 text-xs text-white">
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
                  <button
                    type="button"
                    disabled={addingPaperId !== null}
                    onClick={async () => {
                      const u = gap.paper?.url as string | undefined
                      const pid = gap.paper?.id as string | undefined
                      if (!u) {
                        setError('No ingest URL for this paper.')
                        return
                      }
                      setError(null)
                      setAddingPaperId(pid || u)
                      try {
                        const { data } = await api.post<{ job_id: string }>('/ingest/url', {
                          url: u,
                          workspace_id: workspaceId,
                        })
                        const out = await waitIngestDone(data.job_id)
                        if (out === 'done') {
                          await fetchGaps()
                          onWorkspacePapersChanged?.()
                        } else if (out === 'failed') {
                          setError('Add to workspace failed. Check worker logs.')
                        } else {
                          setError('Ingest still running — refresh in a moment.')
                        }
                      } catch (e: unknown) {
                        const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                        setError(
                          typeof d === 'string' ? d : 'Could not add paper to workspace. Try a Semantic Scholar or DOI link.',
                        )
                      } finally {
                        setAddingPaperId(null)
                      }
                    }}
                    className="text-xs text-teal-400 hover:underline disabled:opacity-40"
                  >
                    {addingPaperId === (gap.paper?.id || gap.paper?.url) ? 'Adding…' : 'Add to workspace →'}
                  </button>
                </div>
              ))}

            {activeTab === 1 && !loading && gaps.semantic_gaps.length === 0 && !scanning && (
              <p className="text-slate-400 text-xs leading-relaxed">
                No conceptual results yet. Run the scan above. You need at least two workspace papers with
                embeddings for a summary; external “gap” clustering needs cited papers that are still{' '}
                <strong>outside</strong> the workspace (see Citation gaps)—adding those papers moves the signal
                back to how your <em>current</em> set relates.
              </p>
            )}

            {activeTab === 1 &&
              gaps.semantic_gaps.map((gap, idx) => (
                <div
                  key={gap.label || gap.cluster_label || `gap-${idx}`}
                  className="space-y-2 rounded-xl border border-white/10 bg-slate-950/55 p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="rounded-full bg-indigo-500/85 px-2 py-0.5 text-xs text-white">
                      {gap.label || gap.cluster_label || 'Cluster'}
                    </span>
                    <span className="text-xs text-slate-400">
                      {Math.round((gap.coverage_score ?? 0) * 100)}% covered
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-700">
                    <div
                      className="h-1.5 rounded-full bg-indigo-400"
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
