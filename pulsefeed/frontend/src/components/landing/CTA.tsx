import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

// Mock feed card — shows what a synthesized PulseFeed brief looks like
function FeedCardPreview() {
  return (
    <div className="relative w-full max-w-sm border-2 border-paper/20 bg-paper/5 font-mono text-paper overflow-hidden">
      {/* Card header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-paper/10 bg-paper/10">
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1.4, repeat: Infinity }}
            className="w-1.5 h-1.5 rounded-full bg-clay"
          />
          <span className="text-[9px] font-bold uppercase tracking-widest text-paper/60">
            [/] SYNTHESIS_OUTPUT
          </span>
        </div>
        <span className="text-[9px] text-paper/30 uppercase tracking-widest">
          READY
        </span>
      </div>

      {/* Topic badge */}
      <div className="px-4 pt-4 pb-2">
        <span
          className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest font-mono"
          style={{
            background: "var(--color-clay)",
            color: "var(--color-paper)",
          }}
        >
          LLM Inference
        </span>
      </div>

      {/* Title */}
      <div className="px-4 pb-3">
        <h4 className="font-display font-bold text-sm uppercase leading-tight text-paper">
          vLLM v0.6: Disaggregated Prefill &amp; Decode Architecture
        </h4>
      </div>

      {/* Summary lines */}
      <div className="px-4 pb-4 space-y-2">
        <div className="h-1.5 w-full bg-paper/20" />
        <div className="h-1.5 w-5/6 bg-paper/15" />
        <div className="h-1.5 w-4/6 bg-paper/10" />
      </div>

      {/* Source + action row */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-paper/10">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border border-paper/20 flex items-center justify-center">
            <div className="w-2 h-2 bg-paper/30" />
          </div>
          <span className="text-[9px] uppercase tracking-widest text-paper/40">
            ArXiv · 2h ago
          </span>
        </div>
        <button className="px-3 py-1 border border-paper/20 text-[9px] font-bold uppercase tracking-widest text-paper/60 hover:border-clay hover:text-clay transition-none">
          [ READ ]
        </button>
      </div>

      {/* Scan line animation overlay */}
      <motion.div
        className="absolute inset-x-0 h-8 pointer-events-none"
        style={{
          background:
            "linear-gradient(to bottom, transparent, rgba(253,252,248,0.04), transparent)",
        }}
        animate={{ top: ["-10%", "110%"] }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "linear",
          repeatDelay: 1.5,
        }}
      />
    </div>
  );
}

// Second preview card (offset / stacked)
function FeedCardPreview2() {
  return (
    <div className="relative w-full max-w-sm border-2 border-paper/10 bg-paper/[0.03] font-mono text-paper overflow-hidden opacity-60">
      <div className="flex items-center justify-between px-4 py-2 border-b border-paper/10">
        <span className="text-[9px] font-bold uppercase tracking-widest text-paper/40">
          [/] QUEUED
        </span>
      </div>
      <div className="px-4 pt-4 pb-2">
        <span className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest font-mono border border-paper/20 text-paper/50">
          System Design
        </span>
      </div>
      <div className="px-4 pb-4 space-y-2 pt-2">
        <div className="h-1.5 w-full bg-paper/10" />
        <div className="h-1.5 w-4/5 bg-paper/8" />
        <div className="h-1.5 w-3/5 bg-paper/6" />
      </div>
    </div>
  );
}

export default function CTA() {
  const navigate = useNavigate();

  return (
    <section className="relative z-10 w-full border-b-4 border-ink bg-ink font-sans overflow-hidden">
      {/* Subtle grid bg */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, var(--color-paper) 0, var(--color-paper) 1px, transparent 1px, transparent 60px), repeating-linear-gradient(90deg, var(--color-paper) 0, var(--color-paper) 1px, transparent 1px, transparent 60px)",
        }}
      />

      <div className="relative z-10 max-w-6xl mx-auto px-4 md:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[60vh]">
          {/* Left: CTA text */}
          <div className="lg:col-span-7 flex flex-col justify-center py-20 md:py-28 lg:pr-16 border-b lg:border-b-0 lg:border-r border-paper/10">
            {/* Tag */}
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-paper/20 mb-10 w-fit">
              <motion.div
                animate={{ opacity: [1, 0, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
                className="w-1.5 h-1.5 rounded-full bg-clay"
              />
              <span className="text-[10px] font-mono font-bold tracking-widest uppercase text-paper/60">
                [!] Action Required // 001
              </span>
            </div>

            <motion.h2
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
              className="text-4xl md:text-5xl xl:text-6xl font-display font-bold text-paper tracking-tighter uppercase leading-[0.95] mb-8"
            >
              High-Signal Context
              <br />
              <span className="italic text-clay">Is The New Leverage.</span>
            </motion.h2>

            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="font-mono text-xs text-paper/50 mb-12 max-w-lg leading-relaxed border-l-2 border-paper/20 pl-4 uppercase tracking-widest"
            >
              Top engineers don't just write more code — they possess the
              architectural awareness to know exactly what is disrupting the
              stack. Secure your operational advantage.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.35 }}
              className="flex flex-col sm:flex-row items-start gap-4"
            >
              <button
                onClick={() => navigate("/onboarding")}
                className="flex items-center gap-4 px-8 py-4 bg-clay text-paper font-display uppercase tracking-wider text-sm font-bold border-2 border-clay hover:bg-paper hover:text-ink hover:border-paper transition-none"
              >
                Initialize Your Swarm →
              </button>
              <div className="flex items-center gap-2 py-4">
                <div className="flex gap-1">
                  {[...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="w-2 h-2 border border-paper/20"
                      style={{
                        background: i < 5 ? "var(--color-clay)" : "transparent",
                      }}
                    />
                  ))}
                </div>
                <span className="font-mono text-[10px] uppercase tracking-widest text-paper/30">
                  200+ active users
                </span>
              </div>
            </motion.div>

            <div className="mt-10 pt-8 border-t border-paper/10">
              <span className="text-[10px] text-paper/30 font-mono font-bold tracking-[2px] uppercase">
                [→] Spend less time sifting. Build.
              </span>
            </div>
          </div>

          {/* Right: Live feed preview */}
          <div className="lg:col-span-5 flex flex-col items-center justify-center py-20 gap-4 lg:pl-12 relative">
            {/* Header label */}
            <div className="w-full max-w-sm flex items-center justify-between mb-2">
              <span className="font-mono text-[9px] uppercase tracking-widest text-paper/40 font-bold">
                [/] Live_Feed_Preview
              </span>
              <motion.span
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="font-mono text-[9px] uppercase tracking-widest font-bold"
                style={{ color: "var(--color-clay)" }}
              >
                ● LIVE
              </motion.span>
            </div>

            {/* Stacked cards */}
            <div className="relative w-full max-w-sm flex flex-col gap-3">
              <FeedCardPreview />
              <FeedCardPreview2 />
            </div>

            {/* More items indicator */}
            <div className="w-full max-w-sm flex items-center gap-3 pt-1">
              <div
                className="flex-1 h-px"
                style={{ background: "rgba(253,252,248,0.08)" }}
              />
              <span className="font-mono text-[9px] uppercase tracking-widest text-paper/20">
                +18 more briefs
              </span>
              <div
                className="flex-1 h-px"
                style={{ background: "rgba(253,252,248,0.08)" }}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
