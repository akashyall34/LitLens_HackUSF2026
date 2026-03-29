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

const WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"

function App() {
  const [selectedPaper, setSelectedPaper] = useState(null as any)
  const [nodes, _setNodes, onNodesChange] = useNodesState([])
  const [edges, _setEdges, onEdgesChange] = useEdgesState([])
  const [blindSpotOpen, setBlindSpotOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [user, setUser] = useState(getUser())
  const [activeEdge, setActiveEdge] = useState(null as any)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })
  const [ingestOpen, setIngestOpen] = useState(false)

  const loadGraph = useCallback(() => {
    if (!user) return
    connectWorkspace(WORKSPACE_ID)
    api
      .get(`/graph/${WORKSPACE_ID}`)
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
  }, [
    user,
    _setNodes,
    _setEdges,
  ])

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

  return (
    <Suspense fallback={null}>
      <div style={{ width: '100vw', height: '100vh', background: '#0f172a' }}>
        <button
          onClick={() => setBlindSpotOpen(true)}
          className="absolute top-4 left-4 z-10 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg"
        >
          View Blind Spots
        </button>
        <button
          onClick={() => setSettingsOpen(true)}
          className="absolute top-4 left-48 z-10 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg"
        >
          Settings
        </button>
        <button
          type="button"
          onClick={() => setIngestOpen(o => !o)}
          className="absolute top-4 left-[19rem] z-10 bg-teal-700 hover:bg-teal-600 text-white text-sm px-3 py-2 rounded-lg"
        >
          Add paper
        </button>
        <button
          onClick={logout}
          className="absolute top-4 right-4 z-10 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg"
        >
          Sign out
        </button>
        <ReactFlow
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
          <Background color="#1e293b" />
          <MiniMap
            nodeColor={node => node.type === 'blindSpotNode' ? '#FF6B6B' : '#4ECDC4'}
            style={{ background: '#1e293b' }}
          />
          <Controls />
        </ReactFlow>
        <PaperDetailPanel
          paper={selectedPaper}
          onClose={() => setSelectedPaper(null)}
          workspaceId={WORKSPACE_ID}
          onRemovedFromWorkspace={loadGraph}
        />
        <BlindSpotPanel
          open={blindSpotOpen}
          onClose={() => setBlindSpotOpen(false)}
          onWorkspacePapersChanged={loadGraph}
        />
        <IngestPaperBar
          open={ingestOpen}
          onClose={() => setIngestOpen(false)}
          onSuccess={loadGraph}
        />
        <RAGQueryBox />
        <WorkspaceSettings
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
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
