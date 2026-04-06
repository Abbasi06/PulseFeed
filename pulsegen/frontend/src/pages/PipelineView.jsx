import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAPI } from '../hooks/useAPI'
import { ADMIN_API_URL, ADMIN_API_KEY } from '../config'

export default function PipelineView() {
  const { data: pipeline, loading, refetch } = useAPI('/pipeline/status', 5000)
  const [triggering, setTriggering] = useState(false)
  const [message, setMessage] = useState('')

  const handleRunNow = async () => {
    setTriggering(true)
    setMessage('')
    try {
      const response = await fetch(`${ADMIN_API_URL}/admin/pipeline/run-now`, {
        method: 'POST',
        headers: { 'X-Admin-Key': ADMIN_API_KEY },
      })
      if (response.ok) {
        const data = await response.json()
        setMessage(data.message || 'harvest_cycle queued')
        setTimeout(() => setMessage(''), 3000)
        refetch()
      } else {
        setMessage('Error triggering pipeline')
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-4xl font-bold text-accent-primary">Pipeline</h1>
        <p className="text-gray-400 mt-2">Monitor and control the ingestion pipeline</p>
      </motion.div>

      {/* Stage Funnel */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-8"
      >
        <h2 className="text-xl font-bold mb-8">Processing Stages</h2>
        <div className="space-y-6">
          {[
            { name: 'Harvested', color: 'primary', width: 100 },
            { name: 'De-duplicated', color: 'healthy', width: 85 },
            { name: 'Gatekeeper', color: 'warning', width: 72 },
            { name: 'Extracted', color: 'warning', width: 68 },
            { name: 'Stored', color: 'healthy', width: 65 },
          ].map((stage, idx) => (
            <div key={idx}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-mono">{stage.name}</span>
                <span className="text-xs text-gray-400">{stage.width}% pass through</span>
              </div>
              <div className="h-8 bg-surface-bg rounded overflow-hidden border border-surface-border">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${stage.width}%` }}
                  transition={{ duration: 1, delay: idx * 0.1 }}
                  className={`h-full bg-gradient-to-r ${
                    stage.color === 'primary'
                      ? 'from-accent-primary to-accent-primary/60'
                      : stage.color === 'healthy'
                        ? 'from-accent-healthy to-accent-healthy/60'
                        : 'from-accent-warning to-accent-warning/60'
                  } flex items-center justify-end pr-3`}
                >
                  <span className="text-xs font-bold text-black">{stage.width}%</span>
                </motion.div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Queue Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 md:grid-cols-2 gap-6"
      >
        <div className="bg-surface-card border border-surface-border rounded p-6">
          <h3 className="text-sm font-mono text-gray-400 uppercase mb-3">Queue Depth</h3>
          <div className="text-4xl font-bold text-accent-primary font-mono">
            {loading ? '—' : pipeline?.queue_depth || 0}
          </div>
          <p className="text-xs text-gray-500 mt-2">pending tasks in Redis</p>
        </div>

        <div className="bg-surface-card border border-surface-border rounded p-6">
          <h3 className="text-sm font-mono text-gray-400 uppercase mb-3">Last Run</h3>
          <div className="text-lg font-mono text-accent-healthy">
            {pipeline?.last_run || '—'}
          </div>
          <p className="text-xs text-gray-500 mt-2">timestamp of last harvest_cycle</p>
        </div>
      </motion.div>

      {/* Run Now Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded p-6 space-y-4"
      >
        <h3 className="text-sm font-mono text-gray-400 uppercase">Manual Trigger</h3>
        <button
          onClick={handleRunNow}
          disabled={triggering}
          className="px-6 py-2 bg-accent-primary text-black font-bold rounded hover:bg-accent-primary/80 disabled:opacity-50 transition"
        >
          {triggering ? 'Queuing...' : 'Run Now'}
        </button>
        {message && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-xs text-accent-healthy font-mono"
          >
            ✓ {message}
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}
