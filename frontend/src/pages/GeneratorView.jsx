import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { GENERATOR_URL } from "../config";

// ---------------------------------------------------------------------------
// Static data
// ---------------------------------------------------------------------------

const PHASES = [
  {
    number: 1,
    name: "Sourcing & Bouncer",
    cost: "$0",
    costColor: "text-emerald-400",
    costBg: "bg-emerald-500/10 border-emerald-500/20",
    description:
      "Async worker polls ArXiv, GitHub, and RSS feeds via mcp-search-tool. Drops documents with fewer than 300 words or spam titles.",
    tools: ["mcp-search-tool", "mcp-sql-tool"],
    icon: "search",
    accent: "violet",
    borderAccent: "border-violet-500/30",
    shadowAccent: "shadow-violet-500/5",
  },
  {
    number: 2,
    name: "Metadata Gatekeeper",
    cost: "Ultra-Low",
    costColor: "text-sky-400",
    costBg: "bg-sky-500/10 border-sky-500/20",
    description:
      "Passes Title, Author, Source, and first 500 chars to gemini-2.5-flash-lite. Discards if is_high_signal=false or confidence < 0.8.",
    tools: ["gemini-2.5-flash-lite"],
    icon: "shield",
    accent: "sky",
    borderAccent: "border-sky-500/30",
    shadowAccent: "shadow-sky-500/5",
  },
  {
    number: 3,
    name: "Deep Extractor",
    cost: "Standard",
    costColor: "text-amber-400",
    costBg: "bg-amber-500/10 border-amber-500/20",
    description:
      "Passes full document to gemini-2.5-flash. Extracts 3-sentence summary, BM25 keywords, taxonomy tags, and image URL. Raw text is discarded.",
    tools: ["gemini-2.5-flash"],
    icon: "zap",
    accent: "amber",
    borderAccent: "border-amber-500/30",
    shadowAccent: "shadow-amber-500/5",
  },
  {
    number: 4,
    name: "Storage Router",
    cost: "$0",
    costColor: "text-emerald-400",
    costBg: "bg-emerald-500/10 border-emerald-500/20",
    description:
      "Routes compressed JSON to three stores: PostgreSQL (source of truth), ChromaDB (vector embeddings), and SQLite FTS5 (BM25 sparse index).",
    tools: ["mcp-sql-tool", "mcp-vector-tool"],
    icon: "database",
    accent: "violet",
    borderAccent: "border-violet-500/30",
    shadowAccent: "shadow-violet-500/5",
  },
];

const CATEGORY_STYLES = {
  Hardware: {
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
    text: "text-purple-300",
    bar: "bg-purple-500",
    headerText: "text-purple-400",
  },
  Architecture: {
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    text: "text-blue-300",
    bar: "bg-blue-500",
    headerText: "text-blue-400",
  },
  Methodology: {
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    text: "text-yellow-300",
    bar: "bg-yellow-500",
    headerText: "text-yellow-400",
  },
  Framework: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-300",
    bar: "bg-emerald-500",
    headerText: "text-emerald-400",
  },
  Model: {
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/30",
    text: "text-cyan-300",
    bar: "bg-cyan-500",
    headerText: "text-cyan-400",
  },
};

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function formatRelativeTime(isoString) {
  if (!isoString) return "—";
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function sourceColor(source) {
  if (!source) return "bg-slate-700/50 text-slate-400";
  const s = source.toLowerCase();
  if (s.includes("arxiv"))
    return "bg-violet-500/10 text-violet-300 border border-violet-500/20";
  if (s.includes("github"))
    return "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20";
  return "bg-sky-500/10 text-sky-300 border border-sky-500/20";
}

// ---------------------------------------------------------------------------
// Phase icon
// ---------------------------------------------------------------------------

function PhaseIcon({ icon, accent }) {
  const colorMap = {
    violet: "text-violet-400",
    sky: "text-sky-400",
    amber: "text-amber-400",
  };
  const cls = `w-4 h-4 ${colorMap[accent] || "text-violet-400"}`;

  if (icon === "search") {
    return (
      <svg
        className={cls}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        viewBox="0 0 24 24"
      >
        <circle cx="11" cy="11" r="8" />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 21l-4.35-4.35"
        />
      </svg>
    );
  }
  if (icon === "shield") {
    return (
      <svg
        className={cls}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"
        />
      </svg>
    );
  }
  if (icon === "zap") {
    return (
      <svg
        className={cls}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.8}
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
        />
      </svg>
    );
  }
  return (
    <svg
      className={cls}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      viewBox="0 0 24 24"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 12c0 1.66-4.03 3-9 3S3 13.66 3 12"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Phase card
// ---------------------------------------------------------------------------

function PhaseCard({ phase }) {
  return (
    <motion.div
      layout
      className={`bg-slate-900 border ${phase.borderAccent} rounded-2xl p-5 flex flex-col gap-3 min-w-[220px] w-[220px] shrink-0 shadow-lg ${phase.shadowAccent}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          {/* Phase number badge with pulse animation */}
          <motion.div
            animate={{ scale: [1, 1.15, 1] }}
            transition={{
              repeat: Infinity,
              duration: 2.5,
              delay: phase.number * 0.4,
            }}
            className="w-6 h-6 rounded-full bg-violet-500/20 border border-violet-500/30 flex items-center justify-center shrink-0"
          >
            <span className="text-[10px] font-bold text-violet-400">
              {phase.number}
            </span>
          </motion.div>
          <div className="flex items-center gap-1.5">
            <PhaseIcon icon={phase.icon} accent={phase.accent} />
            <span className="text-sm font-semibold text-slate-100 leading-tight">
              {phase.name}
            </span>
          </div>
        </div>
      </div>

      {/* Cost badge */}
      <div
        className={`self-start px-2.5 py-0.5 rounded-lg text-xs font-semibold border ${phase.costBg} ${phase.costColor}`}
      >
        {phase.cost}
      </div>

      {/* Description */}
      <p className="text-xs text-slate-400 leading-relaxed flex-1">
        {phase.description}
      </p>

      {/* Tool chips */}
      <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-800">
        {phase.tools.map((tool) => (
          <span
            key={tool}
            className="px-2 py-0.5 bg-slate-800 border border-slate-700/60 rounded-md text-[10px] font-mono text-slate-400"
          >
            {tool}
          </span>
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------

function StatsBar({ stats, loading, error }) {
  if (error) {
    return (
      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/5 border border-amber-500/15 rounded-xl text-xs text-amber-400 mb-5">
        <svg
          className="w-3.5 h-3.5 shrink-0"
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
        Could not load stats — showing pipeline structure only
      </div>
    );
  }

  const tiles = [
    {
      label: "Total Processed",
      value: loading
        ? "—"
        : ((stats?.total_documents ?? "—").toLocaleString?.() ??
          stats?.total_documents ??
          "—"),
      accent: "text-violet-400",
      bg: "bg-violet-500/5 border-violet-500/15",
    },
    {
      label: "ArXiv",
      value: loading ? "—" : (stats?.by_source?.arxiv ?? "—"),
      accent: "text-sky-400",
      bg: "bg-sky-500/5 border-sky-500/15",
    },
    {
      label: "GitHub",
      value: loading ? "—" : (stats?.by_source?.github ?? "—"),
      accent: "text-emerald-400",
      bg: "bg-emerald-500/5 border-emerald-500/15",
    },
    {
      label: "RSS",
      value: loading ? "—" : (stats?.by_source?.rss ?? "—"),
      accent: "text-amber-400",
      bg: "bg-amber-500/5 border-amber-500/15",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className={`border rounded-xl px-4 py-3 ${tile.bg}`}
        >
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1">
            {tile.label}
          </p>
          <p className={`text-xl font-bold ${tile.accent} tabular-nums`}>
            {loading ? (
              <span className="inline-block w-10 h-5 bg-slate-800 rounded animate-pulse" />
            ) : (
              tile.value
            )}
          </p>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Engine offline empty state
// ---------------------------------------------------------------------------

function EngineOffline() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="relative mb-5">
        <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center">
          <svg
            className="w-6 h-6 text-slate-600"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.6}
            viewBox="0 0 24 24"
          >
            <rect x="4" y="4" width="16" height="16" rx="2" />
            <rect x="9" y="9" width="6" height="6" />
            <path d="M15 2v2M15 20v2M9 2v2M9 20v2M2 15h2M20 15h2M2 9h2M20 9h2" />
          </svg>
        </div>
        {/* Animated status dots */}
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            className="absolute -bottom-1 w-1.5 h-1.5 rounded-full bg-slate-700"
            style={{ left: `${28 + i * 8}px` }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ repeat: Infinity, duration: 1.4, delay: i * 0.3 }}
          />
        ))}
      </div>
      <p className="text-sm font-semibold text-slate-400 mb-1">
        Engine Offline
      </p>
      <p className="text-xs text-slate-600 max-w-xs">
        The generator backend is not reachable. The pipeline architecture is
        shown below.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent documents table
// ---------------------------------------------------------------------------

function RecentDocumentsTable({ docs }) {
  if (!docs || docs.length === 0) return null;

  return (
    <div className="mt-8">
      <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
        Recent Documents
      </p>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Source
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">
                  Tags
                </th>
                <th className="text-right px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap hidden sm:table-cell">
                  Confidence
                </th>
                <th className="text-right px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                  Time
                </th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc, i) => (
                <tr
                  key={doc.id ?? i}
                  className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30 transition-colors"
                >
                  <td className="px-4 py-3 text-slate-300 max-w-xs">
                    <p className="truncate text-sm">
                      {doc.title || "Untitled"}
                    </p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span
                      className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${sourceColor(doc.source)}`}
                    >
                      {doc.source || "Unknown"}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    <div className="flex flex-wrap gap-1">
                      {(doc.tags || []).slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="px-1.5 py-0.5 bg-slate-800 border border-slate-700/50 rounded text-[10px] text-slate-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right hidden sm:table-cell">
                    {doc.confidence != null ? (
                      <span
                        className={`text-xs font-semibold tabular-nums ${doc.confidence >= 0.9 ? "text-emerald-400" : doc.confidence >= 0.8 ? "text-sky-400" : "text-amber-400"}`}
                      >
                        {(doc.confidence * 100).toFixed(0)}%
                      </span>
                    ) : (
                      <span className="text-slate-600 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-slate-500 whitespace-nowrap">
                    {formatRelativeTime(doc.processed_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pipeline tab
// ---------------------------------------------------------------------------

function PipelineTab() {
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);
  const intervalRef = useRef(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStats(data);
      setStatsError(null);
    } catch {
      setStatsError("Failed to fetch stats");
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    intervalRef.current = setInterval(fetchStats, 30000);
    return () => clearInterval(intervalRef.current);
  }, [fetchStats]);

  const isOffline = statsError && !stats;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <StatsBar stats={stats} loading={statsLoading} error={statsError} />

      {isOffline && <EngineOffline />}

      {/* Phase flow */}
      <div className="mb-2">
        <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Inference Cascade
        </p>
        {/* Desktop: horizontal scroll row */}
        <div className="hidden sm:flex items-center gap-0 overflow-x-auto pb-3">
          {PHASES.map((phase, idx) => (
            <div key={phase.number} className="flex items-center shrink-0">
              <PhaseCard phase={phase} />
              {idx < PHASES.length - 1 && (
                <div className="flex items-center px-2 shrink-0">
                  <svg
                    className="w-7 h-7 text-slate-700"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
        {/* Mobile: vertical stack */}
        <div className="flex sm:hidden flex-col gap-3">
          {PHASES.map((phase, idx) => (
            <div key={phase.number} className="flex flex-col items-center">
              <div className="w-full">
                <PhaseCard phase={{ ...phase, width: "w-full" }} />
              </div>
              {idx < PHASES.length - 1 && (
                <div className="py-1 text-slate-700">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={1.5}
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {stats?.recent_documents && (
        <RecentDocumentsTable docs={stats.recent_documents.slice(0, 10)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Category bar chart (pure CSS/Framer Motion)
// ---------------------------------------------------------------------------

function CategoryBarChart({ categoryGroups }) {
  const categories = Object.keys(CATEGORY_STYLES);
  const counts = categories.map((cat) => ({
    cat,
    count: categoryGroups[cat]?.length ?? 0,
  }));
  const maxCount = Math.max(...counts.map((c) => c.count), 1);

  return (
    <div className="space-y-2.5">
      {counts.map(({ cat, count }) => {
        const pct = (count / maxCount) * 100;
        const styles = CATEGORY_STYLES[cat];
        return (
          <div key={cat} className="flex items-center gap-3">
            <span className="w-28 text-xs text-slate-400 shrink-0 truncate">
              {cat}
            </span>
            <div className="flex-1 h-5 bg-slate-800 rounded-lg overflow-hidden">
              <motion.div
                className={`h-full rounded-lg ${styles.bar}`}
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <span
              className={`w-6 text-xs font-semibold tabular-nums text-right ${styles.text}`}
            >
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Term chip with tooltip
// ---------------------------------------------------------------------------

function TermChip({ term, context, styles }) {
  return (
    <div className="relative group inline-block">
      <span
        className={`inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium border cursor-default select-none ${styles.bg} ${styles.border} ${styles.text}`}
      >
        {term}
      </span>
      {context && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 max-w-[calc(100vw-2rem)] p-3 bg-slate-800 border border-slate-700 rounded-xl text-xs text-slate-300 shadow-2xl z-20 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          {context}
          {/* Triangle pointer */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-slate-700" />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trend Analyst tab
// ---------------------------------------------------------------------------

function TrendAnalystTab() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Group trends by category
  const categoryGroups = results
    ? (results.extracted_trends ?? []).reduce((acc, trend) => {
        const cat = trend.category || "Methodology";
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(trend);
        return acc;
      }, {})
    : null;

  async function handleAnalyze() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setResults(data);
    } catch (err) {
      setError(err.message || "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left / top: input */}
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Input Document
            </p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste any technical document, ArXiv abstract, blog post, or newsletter snippet…"
              className="w-full h-52 bg-slate-800/60 border border-slate-700 rounded-xl p-4 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500/50 resize-none transition-colors"
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-slate-600">
                {text.length.toLocaleString()} chars
              </span>
              <button
                onClick={handleAnalyze}
                disabled={loading || !text.trim()}
                className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-5 py-2 text-sm font-medium transition-colors"
              >
                {loading ? (
                  <>
                    <svg
                      className="w-4 h-4 animate-spin shrink-0"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        opacity={0.2}
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M21 12a9 9 0 00-9-9"
                      />
                    </svg>
                    Analyzing…
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.8}
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                    Analyze
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2.5 p-3.5 bg-red-950/40 border border-red-500/20 rounded-xl text-xs text-red-300"
            >
              <svg
                className="w-3.5 h-3.5 shrink-0 mt-0.5"
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
              {error}
            </motion.div>
          )}
        </div>

        {/* Right / bottom: results */}
        <div>
          <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Results
          </p>
          <AnimatePresence mode="wait">
            {!results && !loading ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-52 flex flex-col items-center justify-center border border-dashed border-slate-700 rounded-2xl text-center px-6"
              >
                <svg
                  className="w-8 h-8 text-slate-700 mb-3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.4}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="text-sm text-slate-600 font-medium">
                  Results appear here
                </p>
                <p className="text-xs text-slate-700 mt-1">
                  Paste a document and click Analyze
                </p>
              </motion.div>
            ) : loading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-52 flex flex-col items-center justify-center gap-3"
              >
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-full h-8 bg-slate-800 rounded-xl"
                    animate={{ opacity: [0.4, 0.8, 0.4] }}
                    transition={{
                      repeat: Infinity,
                      duration: 1.2,
                      delay: i * 0.2,
                    }}
                  />
                ))}
              </motion.div>
            ) : (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
                className="space-y-6"
              >
                {/* Category breakdown bar chart */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
                    Category Breakdown
                  </p>
                  <CategoryBarChart categoryGroups={categoryGroups} />
                </div>

                {/* Extracted terms grouped by category */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-5">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Extracted Terms
                  </p>
                  {Object.keys(CATEGORY_STYLES).map((cat) => {
                    const terms = categoryGroups[cat];
                    if (!terms || terms.length === 0) return null;
                    const styles = CATEGORY_STYLES[cat];
                    return (
                      <div key={cat}>
                        <div className="flex items-center gap-2 mb-2.5">
                          <span
                            className={`text-xs font-semibold ${styles.headerText}`}
                          >
                            {cat}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${styles.bg} ${styles.border} border ${styles.text}`}
                          >
                            {terms.length}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {terms.map((trend, i) => (
                            <TermChip
                              key={`${trend.term}-${i}`}
                              term={trend.term}
                              context={trend.context}
                              styles={styles}
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Live Run — helpers
// ---------------------------------------------------------------------------

function formatNextRun(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function StatusDot({ state }) {
  if (state === "running") {
    return (
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <motion.span
          className="absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"
          animate={{ scale: [1, 1.8, 1], opacity: [0.75, 0, 0.75] }}
          transition={{ repeat: Infinity, duration: 1.4 }}
        />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-400" />
      </span>
    );
  }
  if (state === "success")
    return (
      <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-400" />
    );
  if (state === "error")
    return <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-red-400" />;
  return (
    <span className="relative flex h-2.5 w-2.5 shrink-0">
      <motion.span
        className="absolute inline-flex h-full w-full rounded-full bg-slate-500 opacity-50"
        animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0.15, 0.5] }}
        transition={{ repeat: Infinity, duration: 2.2 }}
      />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-slate-500" />
    </span>
  );
}

const STATE_TEXT = {
  idle: "text-slate-400",
  running: "text-amber-400",
  success: "text-emerald-400",
  error: "text-red-400",
};

function MiniStat({ label, value }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
        {label}
      </span>
      <span className="text-base font-bold text-slate-200 tabular-nums">
        {value ?? "—"}
      </span>
    </div>
  );
}

function RunNowButton({ generatorState }) {
  const [pending, setPending] = useState(false);
  const [toast, setToast] = useState(null);

  async function handleRunNow() {
    if (pending || generatorState === "running") return;
    setPending(true);
    setToast(null);
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/run-now`, {
        method: "POST",
      });
      if (res.status === 202) setToast({ type: "success", msg: "Run started" });
      else if (res.status === 409)
        setToast({ type: "warn", msg: "Already running" });
      else setToast({ type: "error", msg: `Error ${res.status}` });
    } catch {
      setToast({ type: "error", msg: "Request failed" });
    } finally {
      setPending(false);
      setTimeout(() => setToast(null), 3000);
    }
  }

  return (
    <div className="flex items-center gap-3 mt-3">
      <button
        onClick={handleRunNow}
        disabled={pending || generatorState === "running"}
        className="flex items-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors"
      >
        {pending ? (
          <>
            <svg
              className="w-3.5 h-3.5 animate-spin shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                opacity={0.25}
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 00-9-9"
              />
            </svg>
            Starting…
          </>
        ) : (
          "Run Now"
        )}
      </button>
      <AnimatePresence>
        {toast && (
          <motion.span
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            className={`text-xs font-medium ${toast.type === "success" ? "text-emerald-400" : toast.type === "warn" ? "text-amber-400" : "text-red-400"}`}
          >
            {toast.msg}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

function RunTrendButton({ trendState }) {
  const [pending, setPending] = useState(false);
  const [toast, setToast] = useState(null);

  async function handleRunTrend() {
    if (pending || trendState === "running") return;
    setPending(true);
    setToast(null);
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/run-trend`, { method: "POST" });
      if (res.status === 202) setToast({ type: "success", msg: "Analysis started" });
      else if (res.status === 409) setToast({ type: "warn", msg: "Already running" });
      else setToast({ type: "error", msg: `Error ${res.status}` });
    } catch {
      setToast({ type: "error", msg: "Request failed" });
    } finally {
      setPending(false);
      setTimeout(() => setToast(null), 3000);
    }
  }

  return (
    <div className="flex items-center gap-3 mt-3">
      <button
        onClick={handleRunTrend}
        disabled={pending || trendState === "running"}
        className="flex items-center gap-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors"
      >
        {pending ? (
          <>
            <svg className="w-3.5 h-3.5 animate-spin shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" opacity={0.25} />
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 00-9-9" />
            </svg>
            Starting…
          </>
        ) : (
          "Run Trend Analyst"
        )}
      </button>
      <AnimatePresence>
        {toast && (
          <motion.span
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            className={`text-xs font-medium ${toast.type === "success" ? "text-emerald-400" : toast.type === "warn" ? "text-amber-400" : "text-red-400"}`}
          >
            {toast.msg}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

function AgentCard({
  title,
  state,
  phaseLabel,
  stats,
  lastRun,
  nextRun,
  errorMessage,
  showRunNow,
  showRunTrend,
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <StatusDot state={state} />
          <span className="text-sm font-semibold text-slate-100">{title}</span>
        </div>
        <span
          className={`text-xs font-semibold capitalize ${STATE_TEXT[state] ?? "text-slate-400"}`}
        >
          {state ?? "idle"}
        </span>
      </div>

      {state === "running" && phaseLabel && (
        <div className="self-start px-2.5 py-0.5 bg-amber-500/10 border border-amber-500/25 rounded-lg text-xs font-semibold text-amber-400">
          {phaseLabel}
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-1 border-t border-slate-800">
          {stats.map((s) => (
            <MiniStat key={s.label} label={s.label} value={s.value} />
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800">
        <span>
          Last run:{" "}
          <span className="text-slate-400">{formatRelativeTime(lastRun)}</span>
        </span>
        <span>
          Next: <span className="text-slate-400">{formatNextRun(nextRun)}</span>
        </span>
      </div>

      {state === "error" && errorMessage && (
        <div className="flex items-start gap-2 p-3 bg-red-950/40 border border-red-500/20 rounded-xl text-xs text-red-300">
          <svg
            className="w-3.5 h-3.5 shrink-0 mt-0.5"
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
          {errorMessage}
        </div>
      )}

      {showRunNow && <RunNowButton generatorState={state} />}
      {showRunTrend && <RunTrendButton trendState={state} />}
    </div>
  );
}

function TrendKeywordsPanel({ keywords, collectedAt, docsAnalyzed }) {
  const categoryGroups = keywords
    ? keywords.reduce((acc, kw) => {
        const cat = kw.category || "Methodology";
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(kw);
        return acc;
      }, {})
    : null;

  if (!keywords || keywords.length === 0) {
    return (
      <div className="h-full min-h-[12rem] flex flex-col items-center justify-center border border-dashed border-slate-700 rounded-2xl text-center px-6 py-10">
        <svg
          className="w-8 h-8 text-slate-700 mb-3"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.4}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="text-sm text-slate-600 font-medium">No trend data yet</p>
        <p className="text-xs text-slate-700 mt-1">
          Run the pipeline to collect keywords
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Latest Trend Keywords
        </p>
        <span className="text-xs text-slate-500">
          {docsAnalyzed != null ? `${docsAnalyzed} docs` : ""}
          {collectedAt ? ` · ${formatRelativeTime(collectedAt)}` : ""}
        </span>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
          Category Breakdown
        </p>
        <CategoryBarChart categoryGroups={categoryGroups} />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Extracted Terms
        </p>
        {Object.keys(CATEGORY_STYLES).map((cat) => {
          const terms = categoryGroups[cat];
          if (!terms || terms.length === 0) return null;
          const styles = CATEGORY_STYLES[cat];
          return (
            <div key={cat}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xs font-semibold ${styles.headerText}`}>
                  {cat}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${styles.bg} ${styles.border} border ${styles.text}`}
                >
                  {terms.length}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {terms.map((kw, i) => (
                  <TermChip
                    key={`${kw.term}-${i}`}
                    term={kw.term}
                    context={kw.context}
                    styles={styles}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Live Run tab
// ---------------------------------------------------------------------------

function LiveRunTab() {
  const [agentStatus, setAgentStatus] = useState(null);
  const [keywords, setKeywords] = useState(null);
  const [kwMeta, setKwMeta] = useState({
    collectedAt: null,
    docsAnalyzed: null,
  });
  const prevTrendState = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/agent-status`);
      if (!res.ok) return;
      const data = await res.json();
      setAgentStatus(data);
    } catch {
      /* silent */
    }
  }, []);

  const fetchKeywords = useCallback(async () => {
    try {
      const res = await fetch(`${GENERATOR_URL}/generator/trend-keywords`);
      if (!res.ok) return;
      const data = await res.json();
      setKeywords(data.keywords ?? []);
      setKwMeta({
        collectedAt: data.collected_at ?? null,
        docsAnalyzed: data.docs_analyzed ?? null,
      });
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    fetchStatus(); // eslint-disable-line react-hooks/set-state-in-effect
    fetchKeywords();
    const id = setInterval(fetchStatus, 3000);
    return () => clearInterval(id);
  }, [fetchStatus, fetchKeywords]);

  useEffect(() => {
    const trendState = agentStatus?.trend_analyst?.state;
    if (prevTrendState.current === "running" && trendState === "success")
      fetchKeywords(); // eslint-disable-line react-hooks/set-state-in-effect
    prevTrendState.current = trendState;
  }, [agentStatus, fetchKeywords]);

  const gen = agentStatus?.generator ?? {};
  const trend = agentStatus?.trend_analyst ?? {};

  const genStats = [
    { label: "Harvested", value: gen.docs_harvested },
    { label: "Passed Gate", value: gen.docs_passed_gate },
    { label: "Extracted", value: gen.docs_extracted },
    { label: "Stored", value: gen.docs_stored },
  ];

  const trendStats = [
    { label: "Docs Analyzed", value: trend.docs_analyzed },
    { label: "Trends Found", value: trend.trends_found },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: agent status cards */}
        <div className="flex flex-col gap-4">
          <p className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
            Agent Status
          </p>
          <AgentCard
            title="Generator Pipeline"
            state={gen.state}
            phaseLabel={gen.phase_label}
            stats={genStats}
            lastRun={gen.last_run_at}
            nextRun={gen.next_run_at}
            errorMessage={gen.error_message}
            showRunNow
          />
          <AgentCard
            title="Trend Analyst"
            state={trend.state}
            phaseLabel={trend.phase_label}
            stats={trendStats}
            lastRun={trend.last_run_at}
            nextRun={trend.next_run_at}
            errorMessage={trend.error_message}
            showRunNow={false}
            showRunTrend
          />
        </div>

        {/* Right: trend keywords */}
        <div>
          <TrendKeywordsPanel
            keywords={keywords}
            collectedAt={kwMeta.collectedAt}
            docsAnalyzed={kwMeta.docsAnalyzed}
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab switcher
// ---------------------------------------------------------------------------

const TABS = [
  { id: "pipeline", label: "Pipeline" },
  { id: "trend", label: "Trend Analyst" },
  { id: "live", label: "Live Run" },
];

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function GeneratorView() {
  const [activeTab, setActiveTab] = useState("pipeline");
  const navigate = useNavigate();

  return (
    <div className="h-full flex flex-col bg-slate-950 overflow-hidden">
      {/* Page header */}
      <div className="shrink-0 border-b border-slate-800 px-6 py-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors shrink-0"
            title="Back to Feed"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-xs font-medium hidden sm:inline">Feed</span>
          </button>
          <div className="w-px h-5 bg-slate-800" />
          <div>
            <h1 className="text-lg font-bold text-slate-100">Generator Engine</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              Inference Cascade + Trend Intelligence
            </p>
          </div>
        </div>

        {/* Tab switcher pills */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1 self-start sm:self-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-violet-300"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {activeTab === tab.id && (
                <motion.div
                  layoutId="tab-indicator"
                  className="absolute inset-0 bg-violet-500/10 border border-violet-500/20 rounded-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          {activeTab === "pipeline" ? (
            <motion.div
              key="pipeline"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <PipelineTab />
            </motion.div>
          ) : activeTab === "trend" ? (
            <motion.div
              key="trend"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <TrendAnalystTab />
            </motion.div>
          ) : (
            <motion.div
              key="live"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <LiveRunTab />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
