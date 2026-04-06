import { Component } from 'react'
import PropTypes from 'prop-types'
import { BrowserRouter, Routes, Route, NavLink, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import CommandCenter from './pages/CommandCenter'
import SourcesView from './pages/SourcesView'
import PipelineView from './pages/PipelineView'
import TrendsView from './pages/TrendsView'
import DeadLetterView from './pages/DeadLetterView'
import { useHealthCheck } from './hooks/useHealthCheck'
import { formatDistanceToNow } from './utils/date'

const navLinkClass = ({ isActive }) =>
  `block px-4 py-2 rounded text-sm transition ${
    isActive
      ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
      : 'text-gray-300 hover:bg-surface-bg'
  }`

function NotFoundView() {
  return (
    <div className="p-8 flex flex-col items-center justify-center h-full font-mono">
      <h1 className="text-6xl font-bold text-red-400 mb-4">404</h1>
      <p className="text-gray-400 mb-6">Page not found</p>
      <Link to="/" className="text-accent-primary hover:underline text-sm">
        Back to Command Center
      </Link>
    </div>
  )
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-surface-card border border-red-500/30 p-8 font-mono m-8 rounded">
          <h2 className="text-red-400 text-xl font-bold mb-4">Something went wrong</h2>
          <p className="text-gray-400 text-sm mb-6">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 text-sm bg-red-500/20 text-red-400 border border-red-500/30 rounded hover:bg-red-500/30 transition"
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
}

function App() {
  const { online, lastChecked } = useHealthCheck(15000)

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-surface-bg text-white">
        {/* Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-64 bg-surface-card border-r border-surface-border p-6 flex flex-col"
        >
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-accent-primary">PulseGen</h1>
            <p className="text-xs text-gray-400 mt-1">Admin Console</p>
          </div>

          <nav className="space-y-3 flex-1">
            <NavLink to="/" className={navLinkClass}>
              Command Center
            </NavLink>
            <NavLink to="/sources" className={navLinkClass}>
              Sources
            </NavLink>
            <NavLink to="/pipeline" className={navLinkClass}>
              Pipeline
            </NavLink>
            <NavLink to="/trends" className={navLinkClass}>
              Trends
            </NavLink>
            <NavLink to="/dead-letter" className={navLinkClass}>
              Dead Letter
            </NavLink>
          </nav>

          <div className="text-xs text-gray-500 border-t border-surface-border pt-4">
            <p>v2.0.0</p>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${online ? 'bg-green-400' : 'bg-red-400'}`}
              />
              {online ? (
                <span>Backend online</span>
              ) : (
                <span>
                  Backend unreachable
                  {lastChecked ? ` · ${formatDistanceToNow(lastChecked)}` : ''}
                </span>
              )}
            </div>
          </div>
        </motion.div>

        {/* Main content */}
        <ErrorBoundary>
          <div className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<CommandCenter />} />
              <Route path="/sources" element={<SourcesView />} />
              <Route path="/pipeline" element={<PipelineView />} />
              <Route path="/trends" element={<TrendsView />} />
              <Route path="/dead-letter" element={<DeadLetterView />} />
              <Route path="*" element={<NotFoundView />} />
            </Routes>
          </div>
        </ErrorBoundary>
      </div>
    </BrowserRouter>
  )
}

export default App
