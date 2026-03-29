import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { ReactFlow, Background, MiniMap, Controls, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PaperNode from './components/graph/PaperNode'
import BlindSpotNode from './components/graph/BlindSpotNode'
import { getUser, logout, api } from './lib/auth'
import WorkspaceSettings from './components/WorkspaceSettings'
import { connectWorkspace, edgeAnnotations } from './lib/collaboration'
import EdgeAnnotationMenu from './components/EdgeAnnotationMenu'
import PresenceAvatars from './components/PresenceAvatars'
import IngestPaperBar from './components/IngestPaperBar'

const PaperDetailPanel = lazy(() => import('./components/PaperDetailPanel'))
const BlindSpotPanel = lazy(() => import('./components/BlindSpotPanel'))
const RAGQueryBox = lazy(() => import('./components/RAGQueryBox'))
const AuthPage = lazy(() => import('./components/AuthPage'))

const nodeTypes = {
  paperNode: PaperNode,
  blindSpotNode: BlindSpotNode,
}

function App() {
  const [selectedPaper, setSelectedPaper] = useState(null as any)
  const [nodes, _setNodes, onNodesChange] = useNodesState([])
  const [edges, _setEdges, onEdgesChange] = useEdgesState([])
  const [blindSpotOpen, setBlindSpotOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [user, setUser] = useState(getUser())
  const [workspaceRecoveryErr, setWorkspaceRecoveryErr] = useState(false)
  const [activeEdge, setActiveEdge] = useState(null as any)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })
  const [ingestOpen, setIngestOpen] = useState(false)

  const toolbarBtn =
    'h-9 rounded-lg border border-white/10 bg-slate-900/80 px-3 text-sm font-medium text-slate-100 shadow-sm transition hover:border-cyan-300/40 hover:bg-slate-800/90'
  const primaryToolbarBtn =
    'h-9 rounded-lg border border-cyan-300/40 bg-cyan-500/20 px-3 text-sm font-semibold text-cyan-100 shadow-sm transition hover:bg-cyan-500/30'

  const workspaceId = user?.workspace_id ?? null

  // Refresh workspace_id from server (fixes stale localStorage and legacy demo membership).
  useEffect(() => {
    if (!user?.id) return
    let cancelled = false
    setWorkspaceRecoveryErr(false)
    api
      .get<{ user: { id: string; email: string; workspace_id: string } }>('/auth/me')
      .then(({ data }) => {
        if (cancelled) return
        const merged = { ...user, ...data.user }
        localStorage.setItem('user', JSON.stringify(merged))
        setUser(merged)
      })
      .catch(() => {
        if (!cancelled && !user.workspace_id) setWorkspaceRecoveryErr(true)
      })
    return () => {
      cancelled = true
    }
  }, [user?.id])

  const loadGraph = useCallback(() => {
    if (!user || !workspaceId) return
    connectWorkspace(workspaceId)
    api
      .get(`/graph/${workspaceId}`)
      .then(res => res.data)
      .then(data => {
        _setNodes(
          data.nodes.map((n, i) => ({
            id: n.id,
            type: n.is_blind_spot ? 'blindSpotNode' : 'paperNode',
            position: { x: i * 300, y: 200 },
            data: {
              title: n.title,
              year: n.year,
              clusterColor: n.cluster_color,
              citationCount: n.citation_count,
              onSelect: () => setSelectedPaper(n),
            },
          })),
        )
        _setEdges(
          data.edges.map(e => {
            const edgeStyles = {
              extends: { stroke: '#4ECDC4' },
              contradicts: { stroke: '#FF6B6B', strokeDasharray: '5 5' },
              uses_dataset: { stroke: '#A78BFA' },
              cites: { stroke: '#94A3B8' },
            }
            const style = edgeStyles[e.edge_type] || edgeStyles.cites
            return {
              id: `${e.source}-${e.target}`,
              source: e.source,
              target: e.target,
              label: e.edge_type,
              labelStyle: { fill: '#94A3B8', fontSize: 10 },
              style,
            }
          }),
        )
      })
  }, [user, workspaceId, _setNodes, _setEdges])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  useEffect(() => {
    edgeAnnotations.observe(() => {
      _setEdges(prev => prev.map(e => {
        const key = `${e.source}→${e.target}`
        const annotation = edgeAnnotations.get(key) as any
        if (!annotation) return e
        const edgeStyles = {
          extends:      { stroke: '#4ECDC4' },
          contradicts:  { stroke: '#FF6B6B', strokeDasharray: '5 5' },
          uses_dataset: { stroke: '#A78BFA' },
          cites:        { stroke: '#94A3B8' },
        }
        return { ...e, label: annotation.type, style: edgeStyles[annotation.type] || edgeStyles.cites }
      }))
    })
  }, [])

  if (!user) return (
    <Suspense fallback={null}>
      <AuthPage onAuth={setUser} />
    </Suspense>
  )

  if (!user.workspace_id) {
    if (workspaceRecoveryErr) {
      return (
        <div className="relative min-h-screen overflow-hidden bg-slate-950 px-6 py-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(34,211,238,0.18),transparent_40%),radial-gradient(circle_at_85%_0%,rgba(56,189,248,0.16),transparent_38%)]" />
          <div className="relative mx-auto flex min-h-[70vh] max-w-xl flex-col items-center justify-center gap-4 rounded-2xl border border-white/10 bg-slate-900/70 px-8 text-center text-sm text-slate-300 shadow-2xl backdrop-blur-xl">
            <p>Could not load your workspace. Try signing out and signing in again.</p>
          <button
            type="button"
            onClick={logout}
            className="rounded-lg border border-cyan-300/40 bg-cyan-500/20 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-500/30"
          >
            Sign out
          </button>
          </div>
        </div>
      )
    }
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-300 text-sm">
        Loading workspace…
      </div>
    )
  }

  return (
    <Suspense fallback={null}>
      <div className="relative h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_10%,rgba(34,211,238,0.2),transparent_33%),radial-gradient(circle_at_85%_0%,rgba(56,189,248,0.16),transparent_40%),linear-gradient(180deg,rgba(15,23,42,0.94)_0%,rgba(2,6,23,1)_65%)]" />

        <div className="app-topbar absolute inset-x-4 top-4 z-20 flex items-center justify-between rounded-2xl border border-white/10 bg-slate-900/65 px-4 py-3 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="hidden sm:block">
              <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/75">LitLens</p>
              <h1 className="text-sm font-semibold text-slate-100">Research Graph Workspace</h1>
            </div>
            <button onClick={() => setBlindSpotOpen(true)} className={toolbarBtn}>
              View Blind Spots
            </button>
            <button onClick={() => setSettingsOpen(true)} className={toolbarBtn}>
              Settings
            </button>
            <button type="button" onClick={() => setIngestOpen(o => !o)} className={primaryToolbarBtn}>
              Add paper
            </button>
          </div>
          <button onClick={logout} className={toolbarBtn}>
            Sign out
          </button>
        </div>

        <div className="app-canvas absolute inset-x-4 bottom-4 top-24 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/45 shadow-2xl backdrop-blur-sm">
          <ReactFlow
            className="litness-flow"
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            onEdgeClick={(event, edge) => {
              setMenuPos({ x: event.clientX, y: event.clientY })
              setActiveEdge(edge)
            }}
          >
            <Background color="#334155" gap={24} />
            <MiniMap
              nodeColor={node => node.type === 'blindSpotNode' ? '#FF6B6B' : '#4ECDC4'}
              style={{ background: '#0f172a', border: '1px solid rgba(148, 163, 184, 0.35)' }}
            />
            <Controls />
          </ReactFlow>
        </div>

        <PaperDetailPanel
          paper={selectedPaper}
          onClose={() => setSelectedPaper(null)}
          workspaceId={workspaceId!}
          onRemovedFromWorkspace={loadGraph}
        />
        <BlindSpotPanel
          open={blindSpotOpen}
          onClose={() => setBlindSpotOpen(false)}
          onWorkspacePapersChanged={loadGraph}
          workspaceId={workspaceId!}
        />
        <IngestPaperBar
          open={ingestOpen}
          onClose={() => setIngestOpen(false)}
          onSuccess={loadGraph}
          workspaceId={workspaceId!}
        />
        <RAGQueryBox workspaceId={workspaceId!} />
        <WorkspaceSettings
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          workspaceId={workspaceId!}
        />
        {activeEdge && (
          <div style={{ position: 'fixed', top: menuPos.y, left: menuPos.x }}>
            <EdgeAnnotationMenu
              edge={activeEdge}
              onClose={() => setActiveEdge(null)}
            />
          </div>
        )}
        <PresenceAvatars />
      </div>
    </Suspense>
  )
}

export default App
