import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ExternalLink, Zap, BookMarked, Eye } from "lucide-react";

function Section({ icon: Icon, label, color, children }) {
  return (
    <div>
      <div className={`flex items-center gap-1.5 mb-2`}>
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span
          className={`text-xs font-semibold uppercase tracking-wider ${color}`}
        >
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

export default function InsightBrief({ brief, loading }) {
  const [open, setOpen] = useState(true);

  if (loading) {
    return (
      <div className="mb-6 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 animate-pulse">
        <div className="h-4 w-48 bg-slate-700 rounded mb-3" />
        <div className="h-3 w-full bg-slate-800 rounded mb-2" />
        <div className="h-3 w-3/4 bg-slate-800 rounded" />
      </div>
    );
  }

  if (!brief) return null;

  return (
    <div className="mb-6 rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-950/40 to-slate-900/60 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-violet-500/5 transition-colors"
      >
        <div className="flex items-start gap-2 min-w-0">
          <span className="text-violet-400 text-sm mt-0.5 shrink-0">⚡</span>
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-violet-400 mb-0.5">
              Today's Brief
            </p>
            <p className="text-sm font-medium text-slate-200 leading-snug">
              {brief.headline || "Your personalised insight brief"}
            </p>
          </div>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 shrink-0 mt-0.5 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Collapsible body */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="brief-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-violet-500/10">
              {/* Key Signals */}
              {brief.signals?.length > 0 && (
                <Section
                  icon={Zap}
                  label="Key Signals"
                  color="text-fuchsia-400"
                >
                  <ul className="space-y-1">
                    {brief.signals.map((s, i) => (
                      <li key={i} className="flex items-start gap-1.5">
                        <span className="text-fuchsia-400/60 mt-1 text-[8px]">
                          ●
                        </span>
                        <span className="text-xs text-slate-300 leading-relaxed">
                          {s}
                        </span>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {/* Worth Your Time */}
              {brief.top_reads?.length > 0 && (
                <Section
                  icon={BookMarked}
                  label="Worth Your Time"
                  color="text-violet-400"
                >
                  <ul className="space-y-2">
                    {brief.top_reads.map((r, i) => (
                      <li key={i}>
                        <a
                          href={r.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group flex items-start gap-1.5 hover:text-violet-300 transition-colors"
                        >
                          <ExternalLink className="w-3 h-3 text-violet-500/60 shrink-0 mt-0.5 group-hover:text-violet-400" />
                          <div className="min-w-0">
                            <p className="text-xs text-slate-300 group-hover:text-violet-300 leading-snug line-clamp-2">
                              {r.title}
                            </p>
                            <p className="text-[10px] text-slate-500 mt-0.5">
                              {r.source}
                            </p>
                          </div>
                        </a>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {/* Watch This Space */}
              {brief.watch?.length > 0 && (
                <Section
                  icon={Eye}
                  label="Watch This Space"
                  color="text-blue-400"
                >
                  <div className="flex flex-wrap gap-1.5">
                    {brief.watch.map((w, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/10 border border-blue-500/20 text-blue-300"
                      >
                        {w}
                      </span>
                    ))}
                  </div>
                </Section>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
