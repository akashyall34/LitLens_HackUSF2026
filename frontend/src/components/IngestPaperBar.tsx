import { useState } from 'react'
import { api } from '../lib/auth'

const WORKSPACE_ID = '00000000-0000-0000-0000-000000000001'

async function waitIngestDone(jobId: string): Promise<'done' | 'failed' | 'timeout'> {
  for (let i = 0; i < 90; i++) {
    const { data } = await api.get<{ status: string }>(`/ingest/status/${jobId}`)
    const s = String(data.status ?? '')
    if (s === 'done') return 'done'
    if (s === 'failed') return 'failed'
    await new Promise(r => setTimeout(r, 2000))
  }
  return 'timeout'
}

type Props = {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function IngestPaperBar({ open, onClose, onSuccess }: Props) {
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
        workspace_id: WORKSPACE_ID,
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
        workspace_id: WORKSPACE_ID,
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
    <div className="absolute top-14 right-4 z-20 w-80 rounded-lg border border-slate-600 bg-slate-800 p-4 shadow-xl space-y-3">
      <div className="flex justify-between items-center">
        <p className="text-white text-sm font-medium">Add paper to workspace</p>
        <button type="button" onClick={onClose} className="text-slate-400 text-xs hover:text-white">
          Close
        </button>
      </div>
      <p className="text-slate-500 text-[10px] leading-snug">
        Same workspace for everyone in this demo. Papers are queued to the ingest worker (Semantic Scholar +
        embeddings).
      </p>
      <div className="space-y-1">
        <label className="text-slate-400 text-[10px]">URL (Semantic Scholar or DOI link)</label>
        <input
          value={url}
          onChange={e => setUrl(e.target.value)}
          disabled={busy}
          placeholder="https://www.semanticscholar.org/paper/…"
          className="w-full bg-slate-900 text-white text-xs px-2 py-1.5 rounded border border-slate-600"
        />
        <button
          type="button"
          disabled={busy}
          onClick={runUrl}
          className="w-full bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs py-1.5 rounded"
        >
          Add from URL
        </button>
      </div>
      <div className="space-y-1 pt-1 border-t border-slate-700">
        <label className="text-slate-400 text-[10px]">DOI</label>
        <input
          value={doi}
          onChange={e => setDoi(e.target.value)}
          disabled={busy}
          placeholder="10.xxxx/…"
          className="w-full bg-slate-900 text-white text-xs px-2 py-1.5 rounded border border-slate-600"
        />
        <button
          type="button"
          disabled={busy}
          onClick={runDoi}
          className="w-full bg-slate-600 hover:bg-slate-500 disabled:opacity-50 text-white text-xs py-1.5 rounded"
        >
          Add from DOI
        </button>
      </div>
      {msg && <p className="text-teal-400 text-[10px]">{msg}</p>}
      {err && <p className="text-red-400 text-[10px]">{err}</p>}
    </div>
  )
}
