import { ReactFlow, Background, MiniMap, Controls } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PaperNode from './components/graph/PaperNode'
import BlindSpotNode from './components/graph/BlindSpotNode'

const nodeTypes = {
  paperNode: PaperNode,
  blindSpotNode: BlindSpotNode,
}

const testNodes = [
  {
    id: '1',
    type: 'paperNode',
    position: { x: 250, y: 100 },
    data: {
      title: 'Attention Is All You Need',
      year: 2017,
      clusterColor: '#4ECDC4',
    },
  },
  {
    id: '2',
    type: 'blindSpotNode',
    position: { x: 250, y: 300 },
    data: {
      title: 'Missing Paper',
      year: 2020,
      clusterColor: '#FF6B6B',
    },
  },
]

const testEdges = [
  {
    id: 'e1-2',
    source: '1',
    target: '2',
    style: { stroke: '#94A3B8' },
  },
]

function App() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#0f172a' }}>
      <ReactFlow
        nodes={testNodes}
        edges={testEdges}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background color="#1e293b" />
        <MiniMap
          nodeColor={(node) =>
            node.type === 'blindSpotNode' ? '#FF6B6B' : '#4ECDC4'
          }
          style={{ background: '#1e293b' }}
        />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export default App