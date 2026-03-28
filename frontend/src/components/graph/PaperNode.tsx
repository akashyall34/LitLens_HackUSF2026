import { Handle, Position } from '@xyflow/react'

export default function PaperNode({ data }) {
  return (
    <div
      className="px-4 py-2 rounded-lg shadow-lg border-2 max-w-[200px] cursor-pointer"
      style={{ backgroundColor: '#1e293b', borderColor: data.clusterColor }}
      onClick={data.onSelect}
    >
      <Handle type="target" position={Position.Top} />
      <p className="text-xs font-semibold text-white leading-tight">{data.title}</p>
      <p className="text-xs mt-1" style={{ color: data.clusterColor }}>{data.year}</p>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}