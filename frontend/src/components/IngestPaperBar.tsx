import { useState } from 'react'
import { api } from '../lib/auth'
import { waitIngestDone } from '../lib/waitIngestDone'

type Props = {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  workspaceId: string
}

export default function IngestPaperBar({ open, onClose, onSuccess, workspaceId }: Props) {
  const [url, setUrl] = useState('')
  const [doi, setDoi] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  if (!open) return null

  const runUrl = async () => {
    const u = url.trim()
    if (!u) {
      setErr('Paste a Semantic Scholar URL or paper link.')
      return
    }
    setBusy(true)
    setErr(null)
    setMsg(null)
    try {
      const { data } = await api.post<{ job_id: string }>('/ingest/url', {
        url: u,
        workspace_id: workspaceId,
      })
      setMsg('Ingest started…')
      const out = await waitIngestDone(data.job_id)
      if (out === 'done') {
        setMsg('Paper added. Refreshing graph…')
        setUrl('')
        onSuccess()
      } else if (out === 'failed') setErr('Ingest failed — check API keys and worker logs.')
      else setErr('Still processing — refresh the page in a minute.')
    } catch {
      setErr('Could not start ingest.')
    } finally {
      setBusy(false)
    }
  }

  const runDoi = async () => {
    const d = doi.trim()
    if (!d) {
      setErr('Enter a DOI (e.g. 10.1145/3442188.3445922).')
      return
    }
    setBusy(true)
    setErr(null)
    setMsg(null)
    try {
      const { data } = await api.post<{ job_id: string }>('/ingest/doi', {
        doi: d,
        workspace_id: workspaceId,
      })
      setMsg('Ingest started…')
      const out = await waitIngestDone(data.job_id)
      if (out === 'done') {
        setMsg('Paper added. Refreshing graph…')
        setDoi('')
        onSuccess()
      } else if (out === 'failed') setErr('Ingest failed — check API keys and worker logs.')
      else setErr('Still processing — refresh the page in a minute.')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(typeof detail === 'string' ? detail : 'Could not start ingest.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="absolute right-4 top-20 z-30 w-80 space-y-3 rounded-2xl border border-white/10 bg-slate-900/90 p-4 shadow-2xl backdrop-blur-xl">
      <div className="flex justify-between items-center">
        <div>
          <p className="text-sm font-medium text-slate-100">Add paper to workspace</p>
          <p className="text-[10px] uppercase tracking-[0.16em] text-cyan-200/70">Ingestion</p>
        </div>
        <button type="button" onClick={onClose} className="text-xs text-slate-400 transition hover:text-slate-100">
          Close
        </button>
      </div>
      <p className="text-[10px] leading-snug text-slate-400">
        Papers are queued to the ingest worker (Semantic Scholar +
        embeddings).
      </p>
      <div className="space-y-1 rounded-xl border border-white/10 bg-slate-950/45 p-2">
        <label className="text-[10px] text-slate-300">URL (Semantic Scholar or DOI link)</label>
        <input
          value={url}
          onChange={e => setUrl(e.target.value)}
          disabled={busy}
          placeholder="https://www.semanticscholar.org/paper/…"
          className="w-full rounded border border-white/15 bg-slate-900 px-2 py-1.5 text-xs text-white focus:border-cyan-300/60 focus:outline-none"
        />
        <button
          type="button"
          disabled={busy}
          onClick={runUrl}
          className="w-full rounded border border-cyan-300/40 bg-cyan-500/20 py-1.5 text-xs font-medium text-cyan-100 transition hover:bg-cyan-500/30 disabled:opacity-50"
        >
          Add from URL
        </button>
      </div>
      <div className="space-y-1 rounded-xl border border-white/10 bg-slate-950/45 p-2">
        <label className="text-[10px] text-slate-300">
          DOI (must include the part after the slash)
        </label>
        <input
          value={doi}
          onChange={e => setDoi(e.target.value)}
          disabled={busy}
          placeholder="10.48550/arXiv.1706.03762"
          className="w-full rounded border border-white/15 bg-slate-900 px-2 py-1.5 text-xs text-white focus:border-cyan-300/60 focus:outline-none"
        />
        <button
          type="button"
          disabled={busy}
          onClick={runDoi}
          className="w-full rounded border border-white/15 bg-slate-800 py-1.5 text-xs text-slate-100 transition hover:bg-slate-700 disabled:opacity-50"
        >
          Add from DOI
        </button>
      </div>
      {msg && <p className="text-[10px] text-cyan-300">{msg}</p>}
      {err && <p className="text-red-400 text-[10px]">{err}</p>}
    </div>
  )
}
