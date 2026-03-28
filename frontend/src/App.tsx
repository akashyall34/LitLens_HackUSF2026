import { useState } from 'react'
import { ReactFlow, Background, MiniMap, Controls, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PaperNode from './components/graph/PaperNode'
import BlindSpotNode from './components/graph/BlindSpotNode'
import PaperDetailPanel from './components/PaperDetailPanel'
import { MOCK_GRAPH } from './mocks/graph'

const nodeTypes = {
  paperNode: PaperNode,
  blindSpotNode: BlindSpotNode,
}

function App() {
  const [selectedPaper, setSelectedPaper] = useState(null as any)

  const initialNodes = MOCK_GRAPH.nodes.map((n, i) => ({
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
  }))

  const initialEdges = MOCK_GRAPH.edges.map(e => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    style: { stroke: '#94A3B8' },
  }))

  const [nodes, _setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, _setEdges, onEdgesChange] = useEdgesState(initialEdges)

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0f172a' }}>
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
    </div>
  )
}

export default App
