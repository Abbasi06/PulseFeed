/**
 * BrainLoader — compact version of the hero brain animation.
 * Used on the Dashboard while the AI feed is generating.
 */
import { motion } from 'framer-motion'

const MINI_NODES = [
  { dx: -55, dy: -30, delay: 0.1, color: '#10B981' },
  { dx:  50, dy: -35, delay: 0.5, color: '#60A5FA' },
  { dx: -58, dy:  22, delay: 0.9, color: '#F59E0B' },
  { dx:  52, dy:  28, delay: 1.3, color: '#10B981' },
  { dx:   0, dy: -52, delay: 1.7, color: '#60A5FA' },
]

const CX = 50  // brain centre in the mini SVG
const CY = 42

export default function BrainLoader({ message = 'Researching your feed…' }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 gap-6">
      <div style={{ width: 100, height: 84 }}>
        <svg viewBox="0 0 100 84" style={{ overflow: 'visible', width: '100%', height: '100%' }}>
          <defs>
            <filter id="mini-glow" x="-80%" y="-80%" width="260%" height="260%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Left hemisphere */}
          <motion.path
            d="M 50,10 C 38,10 26,14 19,22 C 12,30 10,40 12,50 C 14,60 20,68 29,73 C 36,77 44,78 50,77 L 50,10 Z"
            fill="none" stroke="#10B981" strokeWidth={1.2} strokeLinecap="round"
            filter="url(#mini-glow)"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.8, ease: [0.4, 0, 0.2, 1], repeat: Infinity, repeatDelay: 1 }}
          />
          {/* Right hemisphere */}
          <motion.path
            d="M 50,10 C 62,10 74,14 81,22 C 88,30 90,40 88,50 C 86,60 80,68 71,73 C 64,77 56,78 50,77 L 50,10 Z"
            fill="none" stroke="#10B981" strokeWidth={1.2} strokeLinecap="round"
            filter="url(#mini-glow)"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.8, ease: [0.4, 0, 0.2, 1], delay: 0.1, repeat: Infinity, repeatDelay: 1 }}
          />
          {/* Fissure */}
          <motion.line x1={50} y1={10} x2={50} y2={77}
            stroke="#10B981" strokeWidth={0.6} strokeOpacity={0.4}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.2, delay: 0.5, repeat: Infinity, repeatDelay: 1.4 }}
          />

          {/* Ingestion nodes */}
          {MINI_NODES.map((n, i) => (
            <motion.circle
              key={i}
              cx={CX} cy={CY} r={3}
              fill={n.color}
              filter="url(#mini-glow)"
              initial={{ x: n.dx, y: n.dy, opacity: 0, scale: 1 }}
              animate={{
                x: 0, y: 0,
                opacity: [0, 1, 1, 0],
                scale: [0.8, 1, 0.8, 0],
              }}
              transition={{
                delay: n.delay,
                duration: 1.6,
                times: [0, 0.2, 0.7, 1],
                ease: 'easeInOut',
                repeat: Infinity,
                repeatDelay: 2.5,
              }}
            />
          ))}

          {/* Pulse ring */}
          <motion.circle
            cx={CX} cy={CY} r={8}
            fill="none" stroke="#10B981" strokeWidth={0.5}
            animate={{ r: [8, 24, 8], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeOut' }}
          />
        </svg>
      </div>

      <div className="text-center">
        <p
          className="text-sm text-slate-400"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
        >
          {message}
        </p>
        <motion.div
          className="mt-2 flex items-center justify-center gap-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="w-1 h-1 rounded-full bg-emerald-500"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, delay: i * 0.25, repeat: Infinity }}
            />
          ))}
        </motion.div>
      </div>
    </div>
  )
}
