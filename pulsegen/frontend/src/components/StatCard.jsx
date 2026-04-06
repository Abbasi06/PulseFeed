import PropTypes from 'prop-types'
import { motion } from 'framer-motion'

export default function StatCard({ label, value, unit = '', icon: Icon, color = 'primary' }) {
  const colorClass = {
    primary: 'bg-accent-primary/10 border-accent-primary/30',
    healthy: 'bg-accent-healthy/10 border-accent-healthy/30',
    warning: 'bg-accent-warning/10 border-accent-warning/30',
    error: 'bg-accent-error/10 border-accent-error/30',
  }[color]

  const iconColorClass = {
    primary: 'text-accent-primary',
    healthy: 'text-accent-healthy',
    warning: 'text-accent-warning',
    error: 'text-accent-error',
  }[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded border ${colorClass} bg-surface-card`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
          <p className="text-3xl font-bold mt-2 font-mono">
            {value != null ? value.toLocaleString() : '—'}
            {unit && <span className="text-lg text-gray-500 ml-1">{unit}</span>}
          </p>
        </div>
        {Icon && <Icon className={`w-5 h-5 ${iconColorClass}`} />}
      </div>
    </motion.div>
  )
}

StatCard.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number,
  unit: PropTypes.string,
  icon: PropTypes.elementType,
  color: PropTypes.oneOf(['primary', 'healthy', 'warning', 'error']),
}
