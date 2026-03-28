import { Handle, Position } from '@xyflow/react'

interface BlindSpotNodeData {
  title: string
  year: number
  clusterColor: string
}

export default function BlindSpotNode({ data }: { data: BlindSpotNodeData }) {
  return (
    <div
      className="px-4 py-2 rounded-lg shadow-lg max-w-[200px]"
      style={{
        backgroundColor: '#1e293b',
        border: '2px dashed #FF6B6B',
      }}
    >
      <Handle type="target" position={Position.Top} />
      <p className="text-xs font-semibold text-white leading-tight">
        {data.title}
      </p>
      <p className="text-xs mt-1 text-red-400">
        {data.year} · Missing
      </p>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}