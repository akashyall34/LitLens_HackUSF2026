import { useState, useEffect } from 'react'
import { ReactFlow, Background, MiniMap, Controls, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PaperNode from './components/graph/PaperNode'
import BlindSpotNode from './components/graph/BlindSpotNode'
import PaperDetailPanel from './components/PaperDetailPanel'
import BlindSpotPanel from './components/BlindSpotPanel'

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


  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/graph/${WORKSPACE_ID}`)
      .then(res => res.json())
      .then(data => {
        _setNodes(data.nodes.map((n, i) => ({
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
        })))
        _setEdges(data.edges.map(e => ({
          id: `${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          style: { stroke: '#94A3B8' },
        })))
      })
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0f172a' }}>
      <button
        onClick={() => setBlindSpotOpen(true)}
        className="absolute top-4 left-4 z-10 bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg"
      >
        View Blind Spots
      </button>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
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
      />
      <BlindSpotPanel
        open={blindSpotOpen}
        onClose={() => setBlindSpotOpen(false)}
      />
    </div>
  )
}

export default App
