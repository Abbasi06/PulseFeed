import { motion } from 'framer-motion'
import { useAPI } from '../hooks/useAPI'
import StatCard from '../components/StatCard'
import { formatDistanceToNow } from '../utils/date'

export default function CommandCenter() {
  const { data: stats, loading: statsLoading } = useAPI('/stats', 5000)
  const { data: pipeline } = useAPI('/pipeline/status', 5000)

  const totalDocs = stats?.total_documents || 0
  const docsToday = stats?.recent_documents?.length || 0
  const activeSources = Object.keys(stats?.by_source || {}).length
  const deadLetterCount = 0 // Will be populated by dead_letter endpoint

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-4xl font-bold text-accent-primary">Command Center</h1>
        <p className="text-gray-400 mt-2">Pipeline overview and operational metrics</p>
      </motion.div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Documents"
          value={totalDocs}
          icon={null}
          color="primary"
        />
        <StatCard
          label="Docs This Session"
          value={docsToday}
          icon={null}
          color="healthy"
        />
        <StatCard
          label="Active Sources"
          value={activeSources}
          icon={null}
          color="warning"
        />
        <StatCard
          label="Queue Depth"
          value={pipeline?.queue_depth || 0}
          icon={null}
          color="error"
        />
      </div>

      {/* Recent Documents */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-6"
      >
        <h2 className="text-xl font-bold mb-4">Recent Documents</h2>
        {statsLoading ? (
          <div className="text-center py-8 text-gray-400">Loading...</div>
        ) : stats?.recent_documents?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs uppercase">
                  <th className="text-left py-3 px-4">Title</th>
                  <th className="text-left py-3 px-4">Source</th>
                  <th className="text-left py-3 px-4">Confidence</th>
                  <th className="text-left py-3 px-4">Processed</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_documents.map((doc, idx) => (
                  <tr
                    key={idx}
                    className="border-t border-surface-border hover:bg-surface-bg transition h-9"
                  >
                    <td className="py-2 px-4 truncate">{doc.title || 'Untitled'}</td>
                    <td className="py-2 px-4 text-accent-primary text-xs">
                      {doc.source}
                    </td>
                    <td className="py-2 px-4">
                      <span className="text-accent-healthy">
                        {(doc.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2 px-4 text-gray-400 text-xs">
                      {doc.processed_at
                        ? formatDistanceToNow(new Date(doc.processed_at))
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">No documents yet</div>
        )}
      </motion.div>

      {/* Pipeline Stage Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-6"
      >
        <h2 className="text-xl font-bold mb-4">Pipeline Stages</h2>
        <div className="flex items-center justify-between">
          {['Harvested', 'Bounced', 'Gated', 'Extracted', 'Stored'].map((stage, i) => (
            <div key={i} className="flex items-center">
              <div className="w-12 h-12 rounded-full bg-accent-primary/20 border border-accent-primary/30 flex items-center justify-center">
                <span className="text-xs font-bold text-accent-primary">{i + 1}</span>
              </div>
              {i < 4 && <div className="h-1 flex-1 mx-2 bg-accent-primary/20" />}
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-between text-xs text-gray-400">
          {['Harvested', 'Bounced', 'Gated', 'Extracted', 'Stored'].map((stage) => (
            <span key={stage}>{stage}</span>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
