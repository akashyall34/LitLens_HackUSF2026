import { api } from './auth'

/**
 * Poll until ingest job finishes. Tolerates short 404 windows before Redis keys exist.
 */
export async function waitIngestDone(jobId: string): Promise<'done' | 'failed' | 'timeout'> {
  for (let i = 0; i < 90; i++) {
    try {
      const { data } = await api.get<{ status: string }>(`/ingest/status/${jobId}`)
      const s = String(data.status ?? '')
      if (s === 'done') return 'done'
      if (s === 'failed') return 'failed'
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status
      if (status === 404 && i < 40) {
        await new Promise(r => setTimeout(r, 1000))
        continue
      }
      throw e
    }
    await new Promise(r => setTimeout(r, 2000))
  }
  return 'timeout'
}
