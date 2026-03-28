import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { useState } from 'react'
import { MOCK_GAPS } from '../mocks/gaps'

const tabs = ['Citation Gaps', 'Conceptual Gaps']

export default function BlindSpotPanel({ open, onClose }) {
  const [activeTab, setActiveTab] = useState(0)
  const gaps = MOCK_GAPS

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ x: '-100%' }}
          animate={{ x: 0 }}
          exit={{ x: '-100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed top-0 left-0 h-full w-96 bg-slate-800 shadow-2xl z-10 flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-slate-700">
            <h2 className="text-white font-semibold text-lg">Blind Spots</h2>
            <button onClick={onClose} className="text-slate-400 hover:text-white">
              <X size={20} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-slate-700">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                className={`flex-1 py-2 text-sm font-medium transition-colors ${
                  activeTab === i
                    ? 'text-teal-400 border-b-2 border-teal-400'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeTab === 0 && gaps.citation_gaps.map(gap => (
              <div key={gap.paper.id} className="bg-slate-700 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-red-500 text-white px-2 py-0.5 rounded-full">
                    Cited by {gap.cited_by_count}
                  </span>
                  <span className="text-xs text-slate-400">{gap.paper.year}</span>
                </div>
                <p className="text-white text-sm font-medium">{gap.paper.title}</p>
                <p className="text-slate-400 text-xs">{gap.paper.authors.join(', ')}</p>
                <p className="text-slate-300 text-xs leading-relaxed">{gap.why_matters}</p>
                <button className="text-xs text-teal-400 hover:underline">
                  Add to workspace →
                </button>
              </div>
            ))}

            {activeTab === 1 && gaps.semantic_gaps.map(gap => (
              <div key={gap.cluster_label} className="bg-slate-700 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs bg-purple-500 text-white px-2 py-0.5 rounded-full">
                    {gap.cluster_label}
                  </span>
                  <span className="text-xs text-slate-400">
                    {Math.round(gap.coverage_score * 100)}% covered
                  </span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-1.5">
                  <div
                    className="bg-purple-400 h-1.5 rounded-full"
                    style={{ width: `${gap.coverage_score * 100}%` }}
                  />
                </div>
                <p className="text-slate-300 text-xs leading-relaxed">{gap.why_matters}</p>
                <div className="space-y-1">
                  {gap.top_papers.slice(0, 3).map(p => (
                    <p key={p.id} className="text-slate-400 text-xs">· {p.title}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
