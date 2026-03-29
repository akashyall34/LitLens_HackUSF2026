import { useState } from 'react'
import { edgeAnnotations } from '../lib/collaboration'

const EDGE_TYPES = ['cites', 'extends', 'contradicts', 'uses_dataset']

export default function EdgeAnnotationMenu({ edge, onClose }) {
  const [selected, setSelected] = useState(edge.data?.edge_type || 'cites')

  const handleSelect = (type) => {
    setSelected(type)
    const key = `${edge.source}→${edge.target}`
    edgeAnnotations.set(key, { type, annotatedBy: localStorage.getItem('user') })
    onClose()
  }

  return (
    <div className="absolute z-20 bg-slate-800 border border-slate-600 rounded-lg p-2 shadow-xl space-y-1">
      {EDGE_TYPES.map(type => (
        <button
          key={type}
          onClick={() => handleSelect(type)}
          className={`w-full text-left text-xs px-3 py-1.5 rounded hover:bg-slate-700 ${
            selected === type ? 'text-teal-400' : 'text-slate-300'
          }`}
        >
          {type}
        </button>
      ))}
    </div>
  )
}
