import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'

export default function PaperDetailPanel({ paper, onClose }) {
  return (
    <AnimatePresence>
      {paper && (
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="fixed top-0 right-0 h-full w-96 bg-slate-800 shadow-2xl z-10 p-6 overflow-y-auto"
        >
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white"
          >
            <X size={20} />
          </button>

          <div className="mt-6 space-y-4">
            <h2 className="text-white font-semibold text-lg leading-snug">
              {paper.title}
            </h2>

            <div className="flex gap-4 text-sm text-slate-400">
              <span>{paper.year}</span>
              <span>{paper.citation_count} citations</span>
            </div>

            {paper.venue && (
              <p className="text-sm text-slate-400 italic">{paper.venue}</p>
            )}

            {paper.abstract && (
              <p className="text-sm text-slate-300 leading-relaxed">
                {paper.abstract}
              </p>
            )}

            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noreferrer"
                className="inline-block text-sm text-teal-400 hover:underline"
              >
                View on Semantic Scholar →
              </a>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
