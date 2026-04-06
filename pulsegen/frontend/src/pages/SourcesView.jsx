import { motion } from 'framer-motion'
import { useAPI } from '../hooks/useAPI'
import { formatDistanceToNow } from '../utils/date'

export default function SourcesView() {
  const { data: sources, loading } = useAPI('/sources', 10000)

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-4xl font-bold text-accent-primary">Sources</h1>
        <p className="text-gray-400 mt-2">Per-connector quality and harvest metrics</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded overflow-hidden"
      >
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading sources...</div>
        ) : sources?.length ? (
          <table className="w-full">
            <thead>
              <tr className="bg-surface-bg border-b border-surface-border text-gray-400 text-xs uppercase tracking-wide">
                <th className="text-left py-3 px-4">Source</th>
                <th className="text-right py-3 px-4">Fetched</th>
                <th className="text-right py-3 px-4">Passed Gate</th>
                <th className="text-right py-3 px-4">Stored</th>
                <th className="text-left py-3 px-4">Pass Rate</th>
                <th className="text-left py-3 px-4">Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source, idx) => (
                <tr
                  key={idx}
                  className="border-t border-surface-border hover:bg-surface-bg/50 transition h-9"
                >
                  <td className="py-3 px-4 font-mono text-sm text-accent-primary">
                    {source.source_id}
                  </td>
                  <td className="py-3 px-4 text-right text-sm font-mono">
                    {source.total_fetched.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right text-sm font-mono text-accent-healthy">
                    {source.total_passed_gate.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-right text-sm font-mono text-accent-warning">
                    {source.total_stored.toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-surface-border rounded overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-accent-error to-accent-healthy transition-all"
                          style={{
                            width: `${Math.min(100, source.pass_rate * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono w-12 text-right">
                        {(source.pass_rate * 100).toFixed(0)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-400">
                    {source.last_updated
                      ? formatDistanceToNow(new Date(source.last_updated))
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-12 text-gray-400">No sources found</div>
        )}
      </motion.div>
    </div>
  )
}
