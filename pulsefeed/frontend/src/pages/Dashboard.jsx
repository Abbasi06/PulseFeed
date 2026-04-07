import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookMarked,
  Eye,
  ExternalLink,
  Calendar,
  MapPin,
  RefreshCw,
} from "lucide-react";
import PulseFeedIcon from "../components/PulseFeedIcon";
import { useAuth } from "../context/AuthContext";
import BrainLoader from "../components/BrainLoader";
import NewsCard from "../components/NewsCard";
import SkeletonCard from "../components/SkeletonCard";
import { API_URL } from "../config";

const TABS = ["Feed", "Events", "Saved"];

// ---------------------------------------------------------------------------
// Toast
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
          ? "bg-neon-pink/20 text-neon-pink border-neon-pink/30"
          : "bg-neon-cyan/20 text-neon-cyan border-neon-cyan/30"
      }`}
    >
      {type === "error" ? (
        <svg
          className="w-4 h-4 shrink-0 text-red-400"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
          />
        </svg>
      ) : (
        <svg
          className="w-4 h-4 shrink-0 text-neon-cyan"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M5 13l4 4L19 7"
          />
        </svg>
      )}
      {message}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Brief tab — glowing pill that expands into a 3-column summary panel
// ---------------------------------------------------------------------------
function BriefTab({ brief, loading, error, onRetry }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mb-5">
      {/* Glowing pill trigger */}
      <div className="relative inline-flex items-center mb-0">
        {/* Blur glow layer */}
        <div className="absolute inset-0 rounded-full blur-md opacity-50 gemini-glow" />
        {/* Gradient border wrapper */}
        <div className="relative p-[1.5px] rounded-full gemini-glow">
          <button
            onClick={() => {
              if (error) {
                onRetry();
                return;
              }
              if (brief) setOpen((o) => !o);
            }}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-space-black text-sm font-bold text-text-primary disabled:opacity-50 transition-opacity select-none"
          >
            <PulseFeedIcon size={11} className="shrink-0" />
            <span>Today's Brief</span>
            {loading && (
              <span className="text-[10px] text-text-secondary">
                generating…
              </span>
            )}
            {error && !loading && (
              <span className="text-[10px] text-neon-pink">retry</span>
            )}
            {brief && !loading && (
              <motion.svg
                animate={{ rotate: open ? 180 : 0 }}
                transition={{ duration: 0.2 }}
                className="w-3 h-3 text-slate-400 shrink-0"
                fill="none"
                stroke="currentColor"
                strokeWidth={2.5}
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19 9l-7 7-7-7"
                />
              </motion.svg>
            )}
          </button>
        </div>
      </div>

      {/* Expandable panel */}
      <AnimatePresence initial={false}>
        {open && brief && (
          <motion.div
            key="brief-panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="overflow-hidden"
          >
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 liquid-glass !rounded-xl !border-deep-purple/40">
              {/* Col 1 — Overview */}
              <div className="px-5 py-4 md:border-r border-b md:border-b-0 border-deep-purple/30">
                <p className="text-[9px] font-bold uppercase tracking-widest text-text-secondary mb-2">
                  Overview
                </p>
                <p className="text-xs text-text-primary leading-relaxed">
                  {brief.headline}
                </p>
                {(brief.watch ?? []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {brief.watch.slice(0, 4).map((w, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-full text-[9px] font-medium bg-sky-500/10 border border-sky-500/20 text-sky-400"
                      >
                        {w}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Col 2 — Key Signals */}
              <div className="px-5 py-4 md:border-r border-b md:border-b-0 border-deep-purple/30">
                <p className="text-[9px] font-bold uppercase tracking-widest text-neon-pink/90 mb-2">
                  Key Signals
                </p>
                <ul className="space-y-2.5">
                  {(brief.signals ?? []).slice(0, 4).map((s, i) => (
                    <li key={i} className="flex items-start gap-2.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-neon-pink/70 shrink-0 mt-1.5" />
                      <span className="text-xs text-text-secondary leading-snug">
                        {s}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Col 3 — Worth Reading */}
              <div className="px-5 py-4">
                <p className="text-[9px] font-bold uppercase tracking-widest text-neon-cyan mb-2">
                  Worth Reading
                </p>
                <ul className="space-y-3">
                  {(brief.top_reads ?? []).slice(0, 3).map((r, i) => (
                    <li key={i}>
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group flex items-start gap-2"
                      >
                        <ExternalLink className="w-3 h-3 shrink-0 mt-0.5 text-text-secondary group-hover:text-neon-cyan transition-colors" />
                        <div className="min-w-0">
                          <p className="text-xs text-text-secondary group-hover:text-neon-cyan transition-colors line-clamp-2 leading-snug">
                            {r.title}
                          </p>
                          {r.source && (
                            <p className="text-[10px] text-text-secondary/60 mt-0.5">
                              {r.source}
                            </p>
                          )}
                        </div>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Event card for the Events tab (fuller version)
// ---------------------------------------------------------------------------
const TYPE_COLORS = {
  Conference: "bg-deep-purple/80",
  Meetup: "bg-neon-cyan/80 text-space-black",
  Workshop: "bg-neon-pink/80",
  Webinar: "bg-deep-purple/60",
  Summit: "bg-neon-pink/60",
};

function EventCard({ name, date, location, type, url, reason }) {
  const safeUrl = url && url !== "#" ? url : null;
  const typeCls =
    TYPE_COLORS[type] ?? "bg-space-black/80 border border-deep-purple/40";
  return (
    <div className="liquid-glass p-4 space-y-3 hover:-translate-y-0.5 flex flex-col">
      {type && (
        <span
          className={`inline-block w-fit px-2.5 py-0.5 rounded-full text-xs font-semibold text-white ${typeCls}`}
        >
          {type}
        </span>
      )}
      {safeUrl ? (
        <a
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-bold text-text-primary leading-snug hover:text-neon-cyan transition-colors"
        >
          {name}
        </a>
      ) : (
        <p className="text-sm font-bold text-text-primary leading-snug">
          {name}
        </p>
      )}
      <div className="flex flex-col gap-1.5 text-xs text-text-secondary">
        {date && (
          <span className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 shrink-0" />
            {date}
          </span>
        )}
        {location && (
          <span className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 shrink-0" />
            {location}
          </span>
        )}
      </div>
      {reason && (
        <p className="text-xs text-text-secondary leading-relaxed flex-1">
          {reason}
        </p>
      )}
      {safeUrl && (
        <a
          href={safeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs font-medium text-neon-cyan hover:text-text-primary transition-colors mt-auto pt-1"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View event
        </a>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const { user } = useAuth();
  const userId = user?.id;

  const [activeTab, setActiveTab] = useState("Feed");
  const [feed, setFeed] = useState([]);
  const [events, setEvents] = useState([]);
  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const pollingRef = useRef(null);

  const fetchBrief = useCallback(() => {
    if (!userId) return;
    setBriefLoading(true);
    setBriefError(false);
    fetch(`${API_URL}/feed/${userId}/brief`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => {
        setBrief(data);
        setBriefError(false);
      })
      .catch(() => {
        setBrief(null);
        setBriefError(true);
      })
      .finally(() => setBriefLoading(false));
  }, [userId]);

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
        if (feedRes.status === 429) {
          const retry = feedRes.headers.get("Retry-After") || "60";
          setToast({
            message: `Feed is fresh — wait ${retry}s before refreshing again`,
            type: "error",
          });
          return;
        }
        if (!feedRes.ok || !eventsRes.ok)
          throw new Error("Failed to load data");
        const [feedData, eventsData] = await Promise.all([
          feedRes.json(),
          eventsRes.json(),
        ]);
        setFeed(feedData);
        setEvents(eventsData);
        const isGenerating =
          feedRes.headers.get("X-Feed-Generating") === "true";
        setGenerating(isGenerating);
        if (feedData.length > 0) {
          fetchBrief();
        } else {
          setBrief(null);
          setBriefError(false);
        }
      } catch (err) {
        setError(err.message || "Could not load your feed. Please try again.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [userId, fetchBrief],
  );

  useEffect(() => {
    loadData(false);
  }, [loadData]);

  // Poll every 8 s while feed is being generated for the first time
  useEffect(() => {
    if (!generating || !userId) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/feed/${userId}`, {
          credentials: "include",
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.length > 0) {
          setFeed(data);
          setGenerating(false);
          fetchBrief();
        } else if (res.headers.get("X-Feed-Generating") !== "true") {
          // Backend finished but returned nothing — stop polling
          setGenerating(false);
        }
      } catch {
        // polling errors are silent — no-empty disabled for this catch
      }
    }, 8000);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [generating, userId, fetchBrief]);

  const toggleFeedLike = useCallback((id) => {
    setFeed((p) =>
      p.map((item) =>
        item.id === id ? { ...item, liked: !item.liked } : item,
      ),
    );
    fetch(`${API_URL}/feed/items/${id}/like`, {
      method: "PATCH",
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((u) => setFeed((p) => p.map((item) => (item.id === id ? u : item))))
      .catch(() => {
        setFeed((p) =>
          p.map((item) =>
            item.id === id ? { ...item, liked: !item.liked } : item,
          ),
        );
        setToast({
          message: "Couldn't update — please try again",
          type: "error",
        });
      });
  }, []);

  const toggleFeedDislike = useCallback((id) => {
    setFeed((p) =>
      p.map((item) =>
        item.id === id ? { ...item, disliked: !item.disliked } : item,
      ),
    );
    fetch(`${API_URL}/feed/items/${id}/dislike`, {
      method: "PATCH",
      credentials: "include",
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((u) => setFeed((p) => p.map((item) => (item.id === id ? u : item))))
      .catch(() =>
        setFeed((p) =>
          p.map((item) =>
            item.id === id ? { ...item, disliked: !item.disliked } : item,
          ),
        ),
      );
  }, []);

  const toggleFeedSave = useCallback((id) => {
    // Optimistic update
    setFeed((p) =>
      p.map((item) =>
        item.id === id ? { ...item, saved: !item.saved } : item,
      ),
    );
    fetch(`${API_URL}/feed/items/${id}/save`, {
      method: "PATCH",
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok)
          return r
            .text()
            .then((t) => Promise.reject(new Error(`${r.status}: ${t}`)));
        return r.json();
      })
      .then((updated) => {
        // Sync with server truth
        setFeed((p) => p.map((item) => (item.id === id ? updated : item)));
      })
      .catch((err) => {
        console.error("[save failed]", err.message);
        // Rollback
        setFeed((p) =>
          p.map((item) =>
            item.id === id ? { ...item, saved: !item.saved } : item,
          ),
        );
        setToast({
          message: "Save failed — is the backend running?",
          type: "error",
        });
      });
  }, []);

  const recordClick = useCallback((id) => {
    setFeed((p) =>
      p.map((item) =>
        item.id === id
          ? { ...item, read_count: (item.read_count || 0) + 1 }
          : item,
      ),
    );
    fetch(`${API_URL}/feed/items/${id}/click`, {
      method: "POST",
      credentials: "include",
    }).catch(() => {});
  }, []);

  const [filterText, setFilterText] = useState("");
  const [filterOpen, setFilterOpen] = useState(false);
  const filterInputRef = useRef(null);
  const q = filterText.trim().toLowerCase();

  const filteredFeed = q
    ? feed.filter((item) =>
        [item.title, item.summary, item.source, item.topic].some((v) =>
          (v || "").toLowerCase().includes(q),
        ),
      )
    : feed;

  const filteredEvents = q
    ? events.filter((ev) =>
        [ev.name, ev.type, ev.location, ev.reason].some((v) =>
          (v || "").toLowerCase().includes(q),
        ),
      )
    : events;

  const savedFeed = feed.filter((item) => item.saved);
  const filteredSaved = q
    ? savedFeed.filter((item) =>
        [item.title, item.summary, item.source, item.topic].some((v) =>
          (v || "").toLowerCase().includes(q),
        ),
      )
    : savedFeed;

  const totalViews = feed.reduce((s, item) => s + (item.read_count || 0), 0);

  return (
    <div className="flex flex-col h-full">
      {/* ── Scrollable body ── */}
      <div className="relative flex-1 min-h-0 overflow-hidden">
        <div className="absolute inset-0 overflow-y-auto scrollbar-hide">
          <div className="max-w-5xl mx-auto px-6 sm:px-10 py-6">
            {/* Error banner */}
            {error && (
              <div className="mb-5 flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
                <svg
                  className="w-5 h-5 text-red-400 shrink-0 mt-0.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                  />
                </svg>
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}

            {/* Tabs + actions */}
            <div className="flex items-center gap-2 mb-6">
              {/* Tab group */}
              <div className="flex gap-1 bg-space-black/80 border border-deep-purple/30 p-1 rounded-xl backdrop-blur-sm">
                {TABS.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`relative px-5 py-1.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                      activeTab === tab
                        ? "text-white"
                        : "text-text-secondary hover:text-text-primary"
                    }`}
                  >
                    {activeTab === tab && (
                      <motion.div
                        layoutId="tab-pill"
                        className="absolute inset-0 bg-deep-purple rounded-lg"
                        transition={{
                          type: "spring",
                          stiffness: 400,
                          damping: 30,
                        }}
                      />
                    )}
                    <span className="relative z-10 flex items-center gap-2">
                      {tab}
                      {!loading && (
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded-full transition-colors ${
                            activeTab === tab
                              ? "bg-space-black text-text-primary shadow-[0_0_8px_var(--color-neon-cyan)]"
                              : "bg-space-black/50 text-text-secondary"
                          }`}
                        >
                          {tab === "Feed"
                            ? filteredFeed.length
                            : tab === "Events"
                              ? filteredEvents.length
                              : filteredSaved.length}
                        </span>
                      )}
                    </span>
                  </button>
                ))}
              </div>

              {/* Expandable keyword filter */}
              <div className="flex items-center gap-1.5 ml-auto">
                <AnimatePresence>
                  {filterOpen && (
                    <motion.div
                      key="filter-input"
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: 168, opacity: 1 }}
                      exit={{ width: 0, opacity: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 380,
                        damping: 32,
                      }}
                      className="overflow-hidden"
                    >
                      <div className="relative flex items-center">
                        <input
                          ref={filterInputRef}
                          type="text"
                          value={filterText}
                          onChange={(e) => setFilterText(e.target.value)}
                          placeholder="Filter by keyword…"
                          className="w-full pl-3 pr-7 py-1.5 text-xs rounded-lg bg-space-black/80 border border-deep-purple/40 text-text-primary placeholder-text-secondary/60 focus:outline-none focus:border-neon-cyan/50 focus:ring-1 focus:ring-neon-cyan/20"
                        />
                        {filterText && (
                          <button
                            onClick={() => setFilterText("")}
                            className="absolute right-2 text-text-secondary hover:text-neon-pink transition-colors"
                          >
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth={2.5}
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M6 18L18 6M6 6l12 12"
                              />
                            </svg>
                          </button>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Filter icon toggle */}
                <button
                  onClick={() => {
                    const next = !filterOpen;
                    setFilterOpen(next);
                    if (!next) setFilterText("");
                    else setTimeout(() => filterInputRef.current?.focus(), 60);
                  }}
                  title="Filter by keyword"
                  className={`w-8 h-8 flex items-center justify-center rounded-lg border transition-colors ${
                    filterOpen || filterText
                      ? "bg-neon-cyan/15 border-neon-cyan/40 text-neon-cyan"
                      : "bg-space-black/80 border-deep-purple/30 text-text-secondary hover:text-text-primary hover:border-deep-purple/50"
                  }`}
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M21 21l-4.35-4.35M17 11A6 6 0 111 11a6 6 0 0116 0z"
                    />
                  </svg>
                </button>

                {/* Refresh icon */}
                <button
                  onClick={() => loadData(true)}
                  disabled={refreshing || loading}
                  title={refreshing ? "Refreshing…" : "Refresh feed"}
                  className="w-8 h-8 flex items-center justify-center rounded-lg border bg-space-black/80 border-deep-purple/30 text-text-secondary hover:text-neon-cyan hover:border-neon-cyan/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
                  />
                </button>

                {!loading && totalViews > 0 && (
                  <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-space-black/60 border border-deep-purple/30 text-neon-cyan text-xs">
                    <Eye className="w-3.5 h-3.5" />
                    {totalViews}
                  </div>
                )}
              </div>
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
              {/* ── Feed tab ── */}
              {activeTab === "Feed" && (
                <motion.div
                  key="feed"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  {/* Brief tab above cards — visible once feed is loaded and has items */}
                  {!loading && feed.length > 0 && (
                    <BriefTab
                      brief={brief}
                      loading={briefLoading}
                      error={briefError}
                      onRetry={fetchBrief}
                    />
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {loading ? (
                      Array.from({ length: 6 }, (_, i) => (
                        <SkeletonCard key={i} />
                      ))
                    ) : generating && feed.length === 0 ? (
                      <div className="col-span-full flex flex-col items-center justify-center py-20">
                        <BrainLoader message="Personalising your feed for the first time…" />
                        <p className="mt-4 text-xs text-slate-500">
                          This takes about 30–60 seconds. We'll update
                          automatically.
                        </p>
                      </div>
                    ) : feed.length === 0 ? (
                      <EmptyState message="No news items yet. Hit the refresh icon to generate your feed." />
                    ) : filteredFeed.length === 0 ? (
                      <EmptyState message={`No results for "${filterText}"`} />
                    ) : (
                      filteredFeed.map((item) => (
                        <NewsCard
                          key={item.id}
                          {...item}
                          onLike={() => toggleFeedLike(item.id)}
                          onDislike={() => toggleFeedDislike(item.id)}
                          onSave={() => toggleFeedSave(item.id)}
                          onReadClick={() => recordClick(item.id)}
                        />
                      ))
                    )}
                  </div>
                </motion.div>
              )}

              {/* ── Events tab ── */}
              {activeTab === "Events" && (
                <motion.div
                  key="events"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  {loading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      {Array.from({ length: 6 }, (_, i) => (
                        <div
                          key={i}
                          className="rounded-2xl bg-slate-900 border border-slate-700/60 p-4 space-y-3 animate-pulse"
                        >
                          <div className="h-5 w-20 rounded-full bg-slate-800" />
                          <div className="space-y-2">
                            <div className="h-3.5 bg-slate-800 rounded w-full" />
                            <div className="h-3.5 bg-slate-800 rounded w-3/4" />
                          </div>
                          <div className="space-y-1.5">
                            <div className="h-3 bg-slate-800 rounded w-2/3" />
                            <div className="h-3 bg-slate-800 rounded w-1/2" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : events.length === 0 ? (
                    <EmptyState message="No events found yet. Hit refresh to discover upcoming conferences and meetups." />
                  ) : filteredEvents.length === 0 ? (
                    <EmptyState message={`No events match "${filterText}"`} />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      {filteredEvents.map((ev) => (
                        <EventCard key={ev.id} {...ev} />
                      ))}
                    </div>
                  )}
                </motion.div>
              )}

              {/* ── Saved tab ── */}
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
                      {Array.from({ length: 3 }, (_, i) => (
                        <SkeletonCard key={i} />
                      ))}
                    </div>
                  ) : savedFeed.length === 0 ? (
                    <EmptyState message="Nothing saved yet. Tap the bookmark icon on any article to save it here." />
                  ) : filteredSaved.length === 0 ? (
                    <EmptyState
                      message={`No saved items match "${filterText}"`}
                    />
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                      {filteredSaved.map((item) => (
                        <NewsCard
                          key={item.id}
                          {...item}
                          onLike={() => toggleFeedLike(item.id)}
                          onDislike={() => toggleFeedDislike(item.id)}
                          onSave={() => toggleFeedSave(item.id)}
                          onReadClick={() => recordClick(item.id)}
                        />
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Refresh overlay */}
        <AnimatePresence>
          {refreshing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10 bg-slate-950/85 backdrop-blur-sm flex items-center justify-center"
            >
              <BrainLoader message="Refreshing your feed…" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Footer — pinned at absolute bottom ── */}
      <div className="shrink-0 border-t border-slate-800 bg-slate-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-4 px-6 py-2.5">
          <div className="flex-1 h-px bg-slate-800" />
          <p className="text-xs text-slate-500 shrink-0">
            Personalised by AI · refreshes every 6 hours
          </p>
          <div className="flex-1 h-px bg-slate-800" />
        </div>
      </div>

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
        <svg
          className="w-7 h-7 text-slate-600"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
          />
        </svg>
      </div>
      <p className="text-sm text-slate-400 max-w-xs leading-relaxed">
        {message}
      </p>
    </div>
  );
}
