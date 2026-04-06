import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAPI } from '../hooks/useAPI'
import { ADMIN_API_URL, ADMIN_API_KEY } from '../config'
import { formatDistanceToNow } from '../utils/date'

export default function DeadLetterView() {
  const { data: deadLetter, loading, refetch } = useAPI('/dead-letter?limit=50', 5000)
  const [retrying, setRetrying] = useState(null)
  const [clearing, setClearing] = useState(false)
  const [message, setMessage] = useState('')

  const handleRetry = async (index) => {
    setRetrying(index)
    setMessage('')
    try {
      const response = await fetch(
        `${ADMIN_API_URL}/admin/dead-letter/${index}/retry`,
        { method: 'POST', headers: { 'X-Admin-Key': ADMIN_API_KEY } },
      )
      if (response.ok) {
        setMessage('Item re-queued')
        setTimeout(() => setMessage(''), 2000)
        refetch()
      } else {
        setMessage('Error retrying item')
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setRetrying(null)
    }
  }

  const handleClearAll = async () => {
    if (!confirm('Clear all dead-letter items? This cannot be undone.')) return
    setClearing(true)
    setMessage('')
    try {
      const response = await fetch(`${ADMIN_API_URL}/admin/dead-letter`, {
        method: 'DELETE',
        headers: { 'X-Admin-Key': ADMIN_API_KEY },
      })
      if (response.ok) {
        const data = await response.json()
        setMessage(`Cleared ${data.count} items`)
        setTimeout(() => setMessage(''), 3000)
        refetch()
      } else {
        setMessage('Error clearing queue')
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`)
    } finally {
      setClearing(false)
    }
  }

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <h1 className="text-4xl font-bold text-accent-error">Dead Letter Queue</h1>
        <p className="text-gray-400 mt-2">
          {deadLetter?.count || 0} failed documents awaiting retry
        </p>
      </motion.div>

      {/* Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex gap-3"
      >
        <button
          onClick={handleClearAll}
          disabled={clearing || !deadLetter?.count}
          className="px-4 py-2 bg-accent-error text-white text-sm font-bold rounded hover:bg-accent-error/80 disabled:opacity-50 transition"
        >
          {clearing ? 'Clearing...' : 'Clear All'}
        </button>
        {message && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-sm text-accent-healthy font-mono"
          >
            ✓ {message}
          </motion.div>
        )}
      </motion.div>

      {/* Dead Letter Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-card border border-surface-border rounded overflow-hidden"
      >
        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading dead letter queue...</div>
        ) : deadLetter?.items?.length ? (
          <table className="w-full">
            <thead>
              <tr className="bg-surface-bg border-b border-surface-border text-gray-400 text-xs uppercase tracking-wide">
                <th className="text-left py-3 px-4">URL</th>
                <th className="text-left py-3 px-4">Title</th>
                <th className="text-left py-3 px-4">Error</th>
                <th className="text-left py-3 px-4">Failed At</th>
                <th className="text-center py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {deadLetter.items.map((item, idx) => (
                <tr key={idx} className="border-t border-surface-border hover:bg-surface-bg/50 transition h-12">
                  <td className="py-3 px-4 truncate max-w-xs">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-primary text-xs hover:underline"
                    >
                      {item.url}
                    </a>
                  </td>
                  <td className="py-3 px-4 truncate text-sm">{item.title || '—'}</td>
                  <td className="py-3 px-4 truncate text-xs text-accent-error max-w-xs">
                    {item.error || '—'}
                  </td>
                  <td className="py-3 px-4 text-xs text-gray-400">
                    {item.failed_at ? formatDistanceToNow(new Date(item.failed_at)) : '—'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={() => handleRetry(idx)}
                      disabled={retrying === idx}
                      className="px-2 py-1 text-xs bg-accent-primary/20 text-accent-primary rounded hover:bg-accent-primary/30 disabled:opacity-50 transition"
                    >
                      {retrying === idx ? '...' : 'Retry'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-12 text-gray-400">
            Queue is clear — no failed documents
          </div>
        )}
      </motion.div>
    </div>
  )
}
