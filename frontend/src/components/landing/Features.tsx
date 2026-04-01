import { motion } from "framer-motion";
import {
  Globe,
  Zap,
  Cpu,
  BarChart3,
  TrendingDown,
} from "lucide-react";

// Signal vs Noise Chart Component
const SignalChart = () => (
  <div className="relative w-full h-24 flex items-end gap-1 px-2 border-b-2 border-ink">
    {[40, 70, 45, 90, 65, 80, 50, 95, 30, 85].map((h, i) => (
      <motion.div
        key={i}
        initial={{ height: 0 }}
        animate={{ height: `${h}%` }}
        transition={{
          duration: 1,
          delay: i * 0.1,
          repeat: Infinity,
          repeatType: "reverse",
        }}
        className={`flex-1 border-ink border-l border-t border-r ${i > 7 ? "bg-clay" : "bg-paper"}`}
      />
    ))}
    <div className="absolute top-0 right-4 p-1 border border-ink text-[8px] font-mono text-clay font-bold uppercase tracking-tighter bg-paper">
      [→] Pure Signal
    </div>
  </div>
);

const features = [
  {
    title: "The Firehose is Unmanageable",
    description:
      "Thousands of repositories, papers, and system design blogs drop every 24 hours. You can't read them all.",
    tag: "[01]",
    icon: Globe,
    className: "md:col-span-2 border-b md:border-b-0",
    visual: () => (
      <div className="mt-8 flex flex-wrap gap-2 overflow-hidden h-14 border-t-2 border-ink pt-4">
        {[
          "ArXiv",
          "GitHub",
          "System Design",
          "vLLM",
          "KEDA",
          "PyTorch",
          "Kubernetes",
          "Next.js",
        ].map((t, i) => (
          <span
            key={i}
            className="px-2 py-0.5 border border-ink text-[9px] font-mono whitespace-nowrap bg-paper text-ink"
          >
            {t}
          </span>
        ))}
      </div>
    ),
  },
  {
    title: "The Noise is Deafening",
    description:
      "Standard aggregators are flooded with SEO bait and marketing fluff that wastes your time.",
    tag: "[02]",
    icon: Zap,
    className: "md:col-span-1 border-b md:border-b-0",
    visual: SignalChart,
  },
  {
    title: "The Cost of Missing Out",
    description:
      "In AI and distributed systems, missing a paradigm shift means building obsolete tech.",
    tag: "[03]",
    icon: Cpu,
    className: "md:col-span-1",
    visual: () => (
      <div className="mt-8 p-4 border-2 border-ink bg-paper">
        <div className="flex justify-between items-center mb-2 pb-2 border-b border-dashed border-ink">
          <span className="text-[10px] text-ink uppercase font-bold tracking-widest font-mono">
            [/] Skill Relevance
          </span>
          <TrendingDown size={14} className="text-clay" />
        </div>
        <div className="text-3xl font-display font-bold text-ink leading-none mt-4 text-center">
          8.4 Months
        </div>
        <p className="text-[9px] text-ink mt-3 font-mono text-center uppercase tracking-tight">
          Average time to architecture obsolescence
        </p>
      </div>
    ),
  },
  {
    title: "Real-time Context Synthesis",
    description:
      "We don't just find links; we synthesize the global technical firehose into actionable intelligence.",
    tag: "[04]",
    icon: BarChart3,
    className: "md:col-span-2",
    visual: () => (
      <div className="mt-8 grid grid-cols-2 gap-4 border-t-2 border-ink pt-6">
        <div className="h-4 w-full border border-ink bg-paper p-[1px]">
          <motion.div
            animate={{ width: ["0%", "100%", "0%"] }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="h-full bg-ink"
          />
        </div>
        <div className="h-4 w-full border border-ink bg-paper p-[1px]">
          <motion.div
            animate={{ width: ["0%", "100%", "0%"] }}
            transition={{ duration: 4, repeat: Infinity, delay: 0.5, ease: "linear" }}
            className="h-full bg-clay"
          />
        </div>
      </div>
    ),
  },
];

export default function Features() {
  return (
    <section className="relative w-full bg-paper font-sans border-b border-ink">
      
      {/* ── SECTION HEADER ── */}
      <div className="w-full border-b-2 border-ink p-6 lg:p-12 text-center bg-paper relative">
        <div className="absolute top-4 left-4 font-mono text-[9px] uppercase tracking-[0.2em] border border-ink p-1">
          [/] Issue 01 // Section B
        </div>
        
        <div className="max-w-4xl mx-auto mt-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-6 bg-paper"
          >
            <span className="text-xs font-mono font-bold tracking-widest uppercase text-ink">
              [/] Engineering Challenges
            </span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-4xl md:text-5xl lg:text-7xl font-bold tracking-tighter text-ink mb-8 leading-[0.9] font-display uppercase"
          >
            The Tech Landscape Moves <br />
            <span className="text-clay italic">
              Too Fast For Manual Tracking.
            </span>
          </motion.h2>

          <motion.p
             initial={{ opacity: 0 }}
             whileInView={{ opacity: 1 }}
             viewport={{ once: true }}
             className="text-base md:text-lg text-ink font-mono max-w-2xl mx-auto leading-relaxed border-l-4 border-ink pl-4 text-left"
          >
            Managing technical context is a bandwidth problem. Standard search
            is obsolete; you need an autonomous swarm to filter the flood.
          </motion.p>
        </div>
      </div>

      {/* ── EDITORIAL SUB-GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-ink">
        {/* Top Row */}
        {features.slice(0, 2).map((feature, i) => (
          <div key={i} className={`p-8 lg:p-12 border-b-2 border-ink ${feature.className} bg-paper hover:bg-[#EEEEEE] transition-none group`}>
            <div className="flex flex-col h-full justify-between">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="w-12 h-12 border-2 border-ink flex items-center justify-center bg-paper group-hover:bg-clay group-hover:text-paper group-hover:border-clay transition-none">
                    <feature.icon size={20} className="text-current" />
                  </div>
                  <span className="text-xs font-mono font-bold text-clay">{feature.tag}</span>
                </div>
                <h3 className="text-2xl font-display font-bold text-ink mb-4 tracking-tight uppercase group-hover:text-clay">
                  {feature.title}
                </h3>
                <p className="text-ink font-mono text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
              <div className="mt-auto">
                {feature.visual && <feature.visual />}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-ink">
         {/* Bottom Row */}
         {features.slice(2).map((feature, i) => (
          <div key={i} className={`p-8 lg:p-12 ${feature.className} bg-paper hover:bg-[#EEEEEE] transition-none group`}>
            <div className="flex flex-col h-full justify-between">
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="w-12 h-12 border-2 border-ink flex items-center justify-center bg-paper group-hover:bg-clay group-hover:text-paper group-hover:border-clay transition-none">
                    <feature.icon size={20} className="text-current" />
                  </div>
                  <span className="text-xs font-mono font-bold text-clay">{feature.tag}</span>
                </div>
                <h3 className="text-2xl font-display font-bold text-ink mb-4 tracking-tight uppercase group-hover:text-clay">
                  {feature.title}
                </h3>
                <p className="text-ink font-mono text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
              <div className="mt-auto">
                {feature.visual && <feature.visual />}
              </div>
            </div>
          </div>
        ))}
      </div>
      
    </section>
  );
}
