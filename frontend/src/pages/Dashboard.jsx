import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  BookMarked,
  Eye,
  ExternalLink,
  Calendar,
  MapPin,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import BrainLoader from "../components/BrainLoader";
import NewsCard from "../components/NewsCard";
import SkeletonCard from "../components/SkeletonCard";
import { API_URL } from "../config";

const TABS = ["Feed", "Saved"];

// ---------------------------------------------------------------------------
// Toast notification
// ---------------------------------------------------------------------------

function Toast({ message, type = "error", onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500);
    return () => clearTimeout(t);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.95 }}
      transition={{ type: "spring", stiffness: 420, damping: 32 }}
      className={`fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2.5 px-4 py-2.5 rounded-xl shadow-2xl text-sm font-medium backdrop-blur-md border whitespace-nowrap ${
        type === "error"
          ? "bg-red-950/90 text-red-200 border-red-500/30 shadow-red-900/40"
          : "bg-emerald-950/90 text-emerald-200 border-emerald-500/30 shadow-emerald-900/40"
      }`}
    >
      {type === "error" ? (
        <svg className="w-4 h-4 shrink-0 text-red-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
      ) : (
        <svg className="w-4 h-4 shrink-0 text-emerald-400" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {message}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Brief panel content
// ---------------------------------------------------------------------------

function BriefContent({ brief, loading }) {
  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-3 w-3/4 bg-slate-800 rounded" />
        <div className="h-3 w-full bg-slate-800 rounded" />
        <div className="h-3 w-2/3 bg-slate-800 rounded" />
        <div className="mt-5 h-3 w-1/2 bg-slate-800 rounded" />
        <div className="h-3 w-full bg-slate-800 rounded" />
        <div className="h-3 w-3/4 bg-slate-800 rounded" />
      </div>
    );
  }
  if (!brief) {
    return (
      <p className="text-xs text-slate-500 leading-relaxed">
        Your brief will appear here after your first feed load.
      </p>
    );
  }
  return (
    <div className="space-y-5">
      <p className="text-sm font-medium text-slate-200 leading-snug">
        {brief.headline}
      </p>

      {brief.signals?.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Zap className="w-3 h-3 text-amber-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
              Key Signals
            </span>
          </div>
          <ul className="space-y-1.5">
            {brief.signals.map((s, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-amber-500/60 mt-1 text-[8px] shrink-0">●</span>
                <span className="text-xs text-slate-300 leading-relaxed">{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {brief.top_reads?.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <BookMarked className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
              Worth Your Time
            </span>
          </div>
          <ul className="space-y-2.5">
            {brief.top_reads.map((r, i) => (
              <li key={i}>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-start gap-1.5 hover:text-emerald-300 transition-colors"
                >
                  <ExternalLink className="w-3 h-3 text-emerald-500/60 shrink-0 mt-0.5 group-hover:text-emerald-400" />
                  <div className="min-w-0">
                    <p className="text-xs text-slate-300 group-hover:text-emerald-300 leading-snug line-clamp-2">
                      {r.title}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{r.source}</p>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {brief.watch?.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Eye className="w-3 h-3 text-sky-400" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-sky-400">
              Watch This Space
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {brief.watch.map((w, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-sky-500/10 border border-sky-500/20 text-sky-300"
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compact event card for the right panel
// ---------------------------------------------------------------------------

const TYPE_COLORS = {
  Conference: "bg-blue-500/80",
  Meetup: "bg-green-500/80",
  Workshop: "bg-amber-500/80",
  Webinar: "bg-cyan-500/80",
  Summit: "bg-rose-500/80",
};

function CompactEventCard({ name, date, location, type, url, reason }) {
  const safeUrl = url && url !== "#" ? url : null;
  const typeCls = TYPE_COLORS[type] ?? "bg-slate-500/80";

  return (
    <div className="rounded-xl bg-slate-800/60 border border-slate-700/50 p-3 space-y-2 hover:border-slate-600 hover:bg-slate-800/80 transition-all duration-200">
      {type && (
        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold text-white ${typeCls}`}>
          {type}
        </span>
      )}
      {safeUrl ? (
        <a
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-xs font-semibold text-slate-200 hover:text-violet-300 transition-colors leading-snug line-clamp-2"
        >
          {name}
        </a>
      ) : (
        <p className="text-xs font-semibold text-slate-200 leading-snug line-clamp-2">{name}</p>
      )}
      <div className="flex flex-col gap-1 text-[10px] text-slate-500">
        {date && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3 shrink-0" />{date}
          </span>
        )}
        {location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3 shrink-0" />
            <span className="truncate">{location}</span>
          </span>
        )}
      </div>
      {reason && (
        <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2 border-t border-slate-700/40 pt-1.5">
          {reason}
        </p>
      )}
      {safeUrl && (
        <a
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] font-medium text-violet-400 hover:text-violet-300 transition-colors pt-0.5"
        >
          <ExternalLink className="w-3 h-3" />
          View event
        </a>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Floating hover panel (Brief on left, Events on right)
// ---------------------------------------------------------------------------

function FloatPanel({ side, open, onOpenChange, collapsedIcon, collapsedLabel, accentColor, children }) {
  const isLeft = side === "left";
  const borderClass = isLeft
    ? "border-r border-t border-b border-l-0 rounded-r-2xl"
    : "border-l border-t border-b border-r-0 rounded-l-2xl";
  const positionClass = isLeft ? "left-0" : "right-0";

  return (
    <div
      className={`absolute ${positionClass} top-1/2 z-20 pointer-events-none hidden md:block`}
      style={{ transform: "translateY(-50%)" }}
    >
      <motion.div
        onHoverStart={() => onOpenChange(true)}
        onHoverEnd={() => onOpenChange(false)}
        animate={{
          width: open ? (isLeft ? 300 : 320) : 44,
          boxShadow: open
            ? `0 20px 60px rgba(0,0,0,0.6), 0 0 40px rgba(183,57,122,0.1)`
            : "0 4px 20px rgba(0,0,0,0.3)",
        }}
        transition={{ type: "spring", stiffness: 380, damping: 36 }}
        className={`pointer-events-auto bg-slate-900/95 backdrop-blur-xl border border-slate-700/60 ${borderClass} overflow-hidden`}
        style={{ minWidth: 44 }}
      >
        {/* Collapsed pill */}
        <motion.div
          animate={{ opacity: open ? 0 : 1, height: open ? 0 : "auto" }}
          transition={{ duration: 0.15 }}
          className="flex flex-col items-center justify-center gap-2 py-5 px-2 overflow-hidden cursor-pointer"
        >
          <span style={{ color: accentColor }}>{collapsedIcon}</span>
          <span
            className="text-[10px] font-semibold tracking-widest text-slate-500 uppercase"
            style={{
              writingMode: "vertical-rl",
              transform: isLeft ? "rotate(180deg)" : "none",
            }}
          >
            {collapsedLabel}
          </span>
        </motion.div>

        {/* Expanded content */}
        <AnimatePresence>
          {open && (
            <motion.div
              key="expanded"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18, delay: 0.08 }}
              className="overflow-y-auto scrollbar-hide p-4 pt-5"
              style={{
                width: isLeft ? 300 : 320,
                maxHeight: "48vh",
              }}
            >
              {/* Panel header */}
              <div className="flex items-center gap-2 mb-4">
                <span style={{ color: accentColor }} className="shrink-0">
                  {collapsedIcon}
                </span>
                <span
                  className="text-[10px] font-semibold uppercase tracking-widest"
                  style={{ color: accentColor }}
                >
                  {collapsedLabel}
                </span>
              </div>
              {children}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const { user } = useAuth();
  const userId = user?.id;

  const [activeTab, setActiveTab] = useState("Feed");
  const [feed, setFeed] = useState([]);
  const [events, setEvents] = useState([]);
  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [briefOpen, setBriefOpen] = useState(false);
  const [eventsOpen, setEventsOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const loadData = useCallback(
    async (force = false) => {
      if (!userId) return;
      force ? setRefreshing(true) : setLoading(true);
      setError("");
      try {
        const method = force ? "POST" : "GET";
        const [feedRes, eventsRes] = await Promise.all([
          fetch(`${API_URL}/feed/${userId}${force ? "/refresh" : ""}`, {
            method,
            credentials: "include",
          }),
          fetch(`${API_URL}/events/${userId}${force ? "/refresh" : ""}`, {
            method,
            credentials: "include",
          }),
        ]);

        // Cooldown response from backend
        if (feedRes.status === 429) {
          const retry = feedRes.headers.get("Retry-After") || "60";
          setToast({ message: `Feed is fresh — wait ${retry}s before refreshing again`, type: "error" });
          return;
        }

        if (!feedRes.ok || !eventsRes.ok) throw new Error("Failed to load data");
        const [feedData, eventsData] = await Promise.all([
          feedRes.json(),
          eventsRes.json(),
        ]);
        setFeed(feedData);
        setEvents(eventsData);

        if (feedData.length > 0) {
          setBriefLoading(true);
          fetch(`${API_URL}/feed/${userId}/brief`, { credentials: "include" })
            .then((r) => (r.ok ? r.json() : null))
            .then((b) => setBrief(b))
            .catch(() => setBrief(null))
            .finally(() => setBriefLoading(false));
        } else {
          setBrief(null);
        }
      } catch (err) {
        setError(err.message || "Could not load your feed. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [userId],
  );

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  // Optimistic like toggle with rollback on failure
  const toggleFeedLike = useCallback(async (id) => {
    setFeed((prev) =>
      prev.map((item) => item.id === id ? { ...item, liked: !item.liked } : item)
    );
    try {
      const res = await fetch(`${API_URL}/feed/items/${id}/like`, {
        method: "PATCH",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Request failed");
      const updated = await res.json();
      setFeed((prev) => prev.map((item) => item.id === id ? updated : item));
    } catch {
      // Rollback
      setFeed((prev) =>
        prev.map((item) => item.id === id ? { ...item, liked: !item.liked } : item)
      );
      setToast({ message: "Couldn't save — please try again", type: "error" });
    }
  }, []);

  const savedFeed = feed.filter((item) => item.liked);

  return (
    <div className="flex flex-col h-screen overflow-hidden">

      {/* ── Body ── */}
      <div className="relative flex-1 overflow-hidden">

        {/* Center scroll area — no scrollbar widget */}
        <div className="h-full overflow-y-auto scrollbar-hide">
          <div className="max-w-5xl mx-auto px-6 sm:px-10 py-6">

            {/* Error banner */}
            {error && (
              <div className="mb-5 flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
                <svg className="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            {/* Tabs */}
            <div className="flex gap-1 bg-slate-900/80 border border-slate-800 p-1 rounded-xl w-fit mb-6 backdrop-blur-sm">
              {TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative px-5 py-1.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                    activeTab === tab
                      ? "text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {activeTab === tab && (
                    <motion.div
                      layoutId="tab-pill"
                      className="absolute inset-0 bg-violet-600 rounded-lg shadow"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center gap-2">
                    {tab}
                    {!loading && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-full transition-colors ${
                        activeTab === tab
                          ? "bg-violet-500/40 text-violet-100"
                          : "bg-slate-800 text-slate-500"
                      }`}>
                        {tab === "Feed" ? feed.length : savedFeed.length}
                      </span>
                    )}
                  </span>
                </button>
              ))}
            </div>

            {/* Tab content with AnimatePresence */}
            <AnimatePresence mode="wait">
              {activeTab === "Feed" && (
                <motion.div
                  key="feed"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
                >
                  {loading ? (
                    Array.from({ length: 6 }, (_, i) => <SkeletonCard key={i} />)
                  ) : feed.length === 0 ? (
                    <EmptyState message="No news items yet. Hit the refresh icon to generate your feed." />
                  ) : (
                    feed.map((item) => (
                      <NewsCard
                        key={item.id}
                        {...item}
                        onLike={() => toggleFeedLike(item.id)}
                      />
                    ))
                  )}
                </motion.div>
              )}

              {activeTab === "Saved" && (
                <motion.div
                  key="saved"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  {loading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      {Array.from({ length: 3 }, (_, i) => <SkeletonCard key={i} />)}
                    </div>
                  ) : savedFeed.length === 0 ? (
                    <EmptyState message="Nothing saved yet. Tap the heart on any article to save it here." />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      {savedFeed.map((item) => (
                        <NewsCard
                          key={item.id}
                          {...item}
                          onLike={() => toggleFeedLike(item.id)}
                        />
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Refresh overlay with BrainLoader */}
        <AnimatePresence>
          {refreshing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="absolute inset-0 z-10 bg-slate-950/85 backdrop-blur-sm flex items-center justify-center"
            >
              <BrainLoader message="Refreshing your feed…" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Left: Today's Brief floating panel ── */}
        <FloatPanel
          side="left"
          open={briefOpen}
          onOpenChange={setBriefOpen}
          collapsedIcon={<Zap className="w-4 h-4" />}
          collapsedLabel="Today's Brief"
          accentColor="#7c3aed"
        >
          <BriefContent brief={brief} loading={briefLoading} />
        </FloatPanel>

        {/* ── Right: Events floating panel ── */}
        <FloatPanel
          side="right"
          open={eventsOpen}
          onOpenChange={setEventsOpen}
          collapsedIcon={<Calendar className="w-4 h-4" />}
          collapsedLabel="Events"
          accentColor="#B7397A"
        >
          {loading ? (
            <div className="space-y-3 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-slate-800 rounded-xl" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <p className="text-xs text-slate-500 leading-relaxed">
              No events found yet. Hit refresh to search for upcoming
              conferences, meetups, and workshops in your field.
            </p>
          ) : (
            <div className="space-y-3">
              {events.map((ev) => (
                <CompactEventCard key={ev.id} {...ev} />
              ))}
            </div>
          )}
        </FloatPanel>
      </div>

      {/* ── Footer ── */}
      <div className="shrink-0 border-t border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="flex items-center justify-center gap-4 px-6 py-2.5">
          <div className="flex-1 h-px bg-slate-800" />
          <p className="text-xs text-slate-500 shrink-0">
            Personalised by AI · refreshes every 6 hours
          </p>
          <div className="flex-1 h-px bg-slate-800" />
          <button
            onClick={() => loadData(true)}
            disabled={refreshing || loading}
            title={refreshing ? "Refreshing…" : "Refresh feed"}
            className="w-7 h-7 flex items-center justify-center rounded-full text-slate-500 hover:text-slate-200 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <Toast
            key="toast"
            message={toast.message}
            type={toast.type}
            onDismiss={() => setToast(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 text-center">
      <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/50 flex items-center justify-center mb-4">
        <svg className="w-7 h-7 text-slate-600" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>
      <p className="text-sm text-slate-400 max-w-xs leading-relaxed">{message}</p>
    </div>
  );
}
