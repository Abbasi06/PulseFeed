import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import CommandCenter from './pages/CommandCenter'
import SourcesView from './pages/SourcesView'
import PipelineView from './pages/PipelineView'
import TrendsView from './pages/TrendsView'
import DeadLetterView from './pages/DeadLetterView'

function App() {
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
            <NavLink
              to="/"
              className={({ isActive }) =>
                `block px-4 py-2 rounded text-sm transition ${
                  isActive
                    ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
                    : 'text-gray-300 hover:bg-surface-bg'
                }`
              }
            >
              Command Center
            </NavLink>
            <NavLink
              to="/sources"
              className={({ isActive }) =>
                `block px-4 py-2 rounded text-sm transition ${
                  isActive
                    ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
                    : 'text-gray-300 hover:bg-surface-bg'
                }`
              }
            >
              Sources
            </NavLink>
            <NavLink
              to="/pipeline"
              className={({ isActive }) =>
                `block px-4 py-2 rounded text-sm transition ${
                  isActive
                    ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
                    : 'text-gray-300 hover:bg-surface-bg'
                }`
              }
            >
              Pipeline
            </NavLink>
            <NavLink
              to="/trends"
              className={({ isActive }) =>
                `block px-4 py-2 rounded text-sm transition ${
                  isActive
                    ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
                    : 'text-gray-300 hover:bg-surface-bg'
                }`
              }
            >
              Trends
            </NavLink>
            <NavLink
              to="/dead-letter"
              className={({ isActive }) =>
                `block px-4 py-2 rounded text-sm transition ${
                  isActive
                    ? 'bg-accent-primary/20 text-accent-primary border-l-2 border-accent-primary'
                    : 'text-gray-300 hover:bg-surface-bg'
                }`
              }
            >
              Dead Letter
            </NavLink>
          </nav>

          <div className="text-xs text-gray-500 border-t border-surface-border pt-4">
            <p>v2.0.0</p>
          </div>
        </motion.div>

        {/* Main content */}
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/sources" element={<SourcesView />} />
            <Route path="/pipeline" element={<PipelineView />} />
            <Route path="/trends" element={<TrendsView />} />
            <Route path="/dead-letter" element={<DeadLetterView />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
