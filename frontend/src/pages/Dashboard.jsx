import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import BrainLoader from '../components/BrainLoader'
import EventCard from '../components/EventCard'
import NewsCard from '../components/NewsCard'
import SkeletonCard from '../components/SkeletonCard'
import { API_URL } from '../config'

const TABS = ['Feed', 'Events', 'Saved']

function RefreshIcon({ spinning }) {
  return (
    <svg
      className={`w-4 h-4 ${spinning ? 'animate-spin' : ''}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const userId = user?.id
  const [activeTab, setActiveTab] = useState('Feed')
  const [feed, setFeed] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadData = useCallback(
    async (force = false) => {
      if (!userId) return
      force ? setRefreshing(true) : setLoading(true)
      setError('')
      try {
        const method = force ? 'POST' : 'GET'
        const [feedRes, eventsRes] = await Promise.all([
          fetch(`${API_URL}/feed/${userId}${force ? '/refresh' : ''}`, { method, credentials: 'include' }),
          fetch(`${API_URL}/events/${userId}${force ? '/refresh' : ''}`, { method, credentials: 'include' }),
        ])
        if (!feedRes.ok || !eventsRes.ok) throw new Error('Failed to load data')
        const [feedData, eventsData] = await Promise.all([feedRes.json(), eventsRes.json()])
        setFeed(feedData)
        setEvents(eventsData)
      } catch (err) {
        setError(err.message || 'Could not load your feed. Please try again.')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [userId],
  )

  useEffect(() => {
    loadData(false)
  }, [loadData])

  const toggleFeedLike = useCallback(async (id) => {
    const res = await fetch(`${API_URL}/feed/items/${id}/like`, { method: 'PATCH', credentials: 'include' })
    if (!res.ok) return
    const updated = await res.json()
    setFeed(prev => prev.map(item => item.id === id ? updated : item))
  }, [])

  const toggleEventLike = useCallback(async (id) => {
    const res = await fetch(`${API_URL}/events/items/${id}/like`, { method: 'PATCH', credentials: 'include' })
    if (!res.ok) return
    const updated = await res.json()
    setEvents(prev => prev.map(ev => ev.id === id ? updated : ev))
  }, [])

  const savedFeed = feed.filter(item => item.liked)
  const savedEvents = events.filter(ev => ev.liked)
  const savedCount = savedFeed.length + savedEvents.length

  const skeletons = Array.from({ length: 6 })

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white">Your Feed</h2>
          <p className="text-sm text-slate-400 mt-0.5">Personalised by AI · refreshes every 6 hours</p>
        </div>
        <button
          onClick={() => loadData(true)}
          disabled={refreshing || loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700 rounded-lg text-sm text-slate-200 font-medium transition-colors"
        >
          <RefreshIcon spinning={refreshing} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          <svg className="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl w-fit mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab
                ? 'bg-violet-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab}
            {!loading && (
              <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                activeTab === tab ? 'bg-violet-500/40 text-violet-100' : 'bg-slate-800 text-slate-400'
              }`}>
                {tab === 'Feed' ? feed.length : tab === 'Events' ? events.length : savedCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Feed Tab */}
      {activeTab === 'Feed' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {loading
            ? <BrainLoader message="Researching your feed…" />
            : feed.length === 0
            ? <EmptyState message="No news items yet. Hit Refresh to generate your feed." />
            : feed.map((item) => (
                <NewsCard key={item.id} {...item} onLike={() => toggleFeedLike(item.id)} />
              ))
          }
        </div>
      )}

      {/* Events Tab */}
      {activeTab === 'Events' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {loading
            ? <BrainLoader message="Scanning for upcoming events…" />
            : events.length === 0
            ? <EmptyState message="No events found yet. Hit Refresh to search for upcoming events." />
            : events.map((ev) => (
                <EventCard key={ev.id} {...ev} onLike={() => toggleEventLike(ev.id)} />
              ))
          }
        </div>
      )}

      {/* Saved Tab */}
      {activeTab === 'Saved' && (
        <div className="space-y-8">
          {savedFeed.length === 0 && savedEvents.length === 0 ? (
            <EmptyState message="Nothing saved yet. Tap the heart on any article or event to save it here." />
          ) : (
            <>
              {savedFeed.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Saved Articles</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {savedFeed.map(item => (
                      <NewsCard key={item.id} {...item} onLike={() => toggleFeedLike(item.id)} />
                    ))}
                  </div>
                </section>
              )}
              {savedEvents.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Saved Events</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {savedEvents.map(ev => (
                      <EventCard key={ev.id} {...ev} onLike={() => toggleEventLike(ev.id)} />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function EmptyState({ message }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mb-4">
        <svg className="w-6 h-6 text-slate-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>
      <p className="text-sm text-slate-400 max-w-xs">{message}</p>
    </div>
  )
}
