import { motion } from 'framer-motion'
import { useAPI } from '../hooks/useAPI'
import { formatDistanceToNow } from '../utils/date'

export default function TrendsView() {
  const { data: keywords, loading: keywordsLoading } = useAPI('/trends/keywords', 10000)
  const { data: runs } = useAPI('/trends/runs', 10000)

  const categoryColors = {
    technology: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    science: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    business: 'bg-green-500/20 text-green-300 border-green-500/30',
    health: 'bg-red-500/20 text-red-300 border-red-500/30',
    general: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
  }

  const getCategoryColor = (category) => {
    return categoryColors[category?.toLowerCase()] || categoryColors.general
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-4xl font-bold text-accent-primary">Trends</h1>
        <p className="text-gray-400 mt-2">Real-time trend analysis across sources</p>
      </motion.div>

      {/* Keyword Chips */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-6"
      >
        <h2 className="text-xl font-bold mb-4">Trending Keywords</h2>
        {keywordsLoading ? (
          <div className="text-center py-8 text-gray-400">Loading keywords...</div>
        ) : keywords?.length ? (
          <div className="flex flex-wrap gap-3">
            {keywords.slice(0, 30).map((kw, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.02 }}
                className={`px-3 py-1.5 rounded-full border text-xs font-mono ${getCategoryColor(
                  kw.category,
                )}`}
              >
                {kw.term}
                {kw.source_count > 1 && (
                  <span className="ml-1 opacity-70">({kw.source_count})</span>
                )}
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">No keywords yet</div>
        )}
      </motion.div>

      {/* Runs Timeline */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-6"
      >
        <h2 className="text-xl font-bold mb-4">Analysis Runs</h2>
        {runs?.length ? (
          <div className="space-y-3">
            {runs.map((run, idx) => (
              <div
                key={idx}
                className="border border-surface-border rounded p-3 hover:bg-surface-bg/50 transition"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-mono text-sm text-accent-primary">{run.run_id}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {run.docs_analyzed.toLocaleString()} documents analyzed
                    </p>
                  </div>
                  <span className="text-xs text-gray-500">
                    {run.collected_at
                      ? formatDistanceToNow(new Date(run.collected_at))
                      : '—'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">No runs yet</div>
        )}
      </motion.div>
    </div>
  )
}
