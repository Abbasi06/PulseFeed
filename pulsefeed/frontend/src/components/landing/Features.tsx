import { motion } from "framer-motion";
import { Globe, Zap, Cpu, BarChart3, TrendingDown } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

// ── Types ──────────────────────────────────────────────────────────────────

interface Feature {
  tag: string;
  icon: LucideIcon;
  title: string;
  description: string;
  visual: () => ReactNode;
}

// ── Visual anchors ─────────────────────────────────────────────────────────

const TagCloud = () => (
  <div className="flex flex-wrap gap-2 pt-4 border-t border-ink">
    {[
      "ArXiv",
      "GitHub",
      "System Design",
      "vLLM",
      "KEDA",
      "PyTorch",
      "Kubernetes",
      "Next.js",
    ].map((t) => (
      <span
        key={t}
        className="px-2 py-0.5 border border-ink text-[9px] font-mono text-ink"
      >
        {t}
      </span>
    ))}
  </div>
);

const SignalChart = () => (
  <div className="relative pt-4 border-t border-ink">
    <div className="relative w-full h-20 flex items-end gap-[3px]">
      {[40, 70, 45, 90, 65, 80, 50, 95, 30, 85].map((h, i) => (
        <motion.div
          key={i}
          initial={{ height: 0 }}
          animate={{ height: `${h}%` }}
          transition={{
            duration: 1,
            delay: i * 0.08,
            repeat: Infinity,
            repeatType: "reverse",
          }}
          className={`flex-1 border border-ink ${i > 7 ? "bg-clay" : "bg-paper"}`}
        />
      ))}
    </div>
    <span className="absolute top-6 right-0 text-[8px] font-mono text-clay font-bold uppercase border border-ink bg-paper px-1">
      [→] Pure Signal
    </span>
  </div>
);

const ObsolescenceStat = () => (
  <div className="pt-4 border-t border-ink">
    <div className="p-4 border border-ink">
      <div className="flex justify-between items-center pb-2 border-b border-dashed border-ink mb-3">
        <span className="text-[9px] font-mono uppercase tracking-widest font-bold text-ink">
          [/] Skill Relevance
        </span>
        <TrendingDown size={12} className="text-clay" />
      </div>
      <div className="text-3xl font-display font-bold text-ink text-center leading-none">
        8.4 Months
      </div>
      <p className="text-[9px] font-mono text-center uppercase tracking-tight mt-2 text-ink">
        Avg. time to architecture obsolescence
      </p>
    </div>
  </div>
);

const SynthesisProgress = () => (
  <div className="pt-4 border-t border-ink space-y-3">
    <div className="h-3 w-full border border-ink bg-paper p-[2px]">
      <motion.div
        animate={{ width: ["0%", "100%", "0%"] }}
        transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        className="h-full bg-ink"
      />
    </div>
    <div className="h-3 w-full border border-ink bg-paper p-[2px]">
      <motion.div
        animate={{ width: ["0%", "100%", "0%"] }}
        transition={{
          duration: 4,
          repeat: Infinity,
          delay: 0.6,
          ease: "linear",
        }}
        className="h-full bg-clay"
      />
    </div>
  </div>
);

// ── Feature data (2-col equal grid — no mixed col-spans) ───────────────────

const FEATURES: Feature[] = [
  {
    tag: "[01]",
    icon: Globe,
    title: "The Firehose is Unmanageable",
    description:
      "Thousands of repositories, papers, and system design blogs drop every 24 hours. You can't read them all.",
    visual: TagCloud,
  },
  {
    tag: "[02]",
    icon: Zap,
    title: "The Noise is Deafening",
    description:
      "Standard aggregators are flooded with SEO bait and marketing fluff that wastes your time.",
    visual: SignalChart,
  },
  {
    tag: "[03]",
    icon: Cpu,
    title: "The Cost of Missing Out",
    description:
      "In AI and distributed systems, missing a paradigm shift means building obsolete tech.",
    visual: ObsolescenceStat,
  },
  {
    tag: "[04]",
    icon: BarChart3,
    title: "Real-time Context Synthesis",
    description:
      "We don't just find links; we synthesize the global technical firehose into actionable intelligence.",
    visual: SynthesisProgress,
  },
];

// ── Card ───────────────────────────────────────────────────────────────────

function FeatureCard({
  tag,
  icon: Icon,
  title,
  description,
  visual: Visual,
}: Feature) {
  return (
    <div className="bg-paper p-8 lg:p-10 flex flex-col gap-5 group hover:bg-[#F5F4F0] transition-none">
      {/* Row 1: icon + tag number */}
      <div className="flex items-start justify-between">
        <div
          className="w-10 h-10 border-2 border-ink flex items-center justify-center shrink-0
                        group-hover:bg-clay group-hover:border-clay group-hover:text-paper transition-none"
        >
          <Icon size={16} className="text-ink group-hover:text-paper" />
        </div>
        <span className="text-xs font-mono font-bold text-clay tracking-widest">
          {tag}
        </span>
      </div>

      {/* Row 2: title */}
      <h3
        className="text-lg md:text-xl font-display font-bold text-ink uppercase tracking-tight leading-tight
                     group-hover:text-clay transition-none"
      >
        {title}
      </h3>

      {/* Row 3: description */}
      <p className="text-[13px] font-mono text-ink leading-relaxed">
        {description}
      </p>

      {/* Row 4: visual anchor (chart / cloud / stat) */}
      <div className="mt-auto">
        <Visual />
      </div>
    </div>
  );
}

// ── Section ────────────────────────────────────────────────────────────────

export default function Features() {
  return (
    <section
      id="features"
      className="relative z-10 w-full bg-paper border-b-2 border-ink font-sans"
    >
      {/* ── Centered container ── */}
      <div className="max-w-6xl mx-auto px-4 md:px-8">
        {/* Section header */}
        <div className="py-16 md:py-20 text-center border-b-2 border-ink">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-8"
          >
            <span className="text-[11px] font-mono font-bold tracking-widest uppercase text-ink">
              [/] Engineering Challenges
            </span>
          </motion.div>

          {/* Heading */}
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold font-display tracking-tighter
                       text-ink leading-[0.9] uppercase mb-8"
          >
            The Tech Landscape Moves <br />
            <span className="text-clay italic">
              Too Fast For Manual Tracking.
            </span>
          </motion.h2>

          {/* Descriptor */}
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="text-sm md:text-base font-mono text-ink max-w-xl mx-auto
                       leading-relaxed border-l-4 border-ink pl-4 text-left"
          >
            Managing technical context is a bandwidth problem. Standard search
            is obsolete; you need an autonomous swarm to filter the flood.
          </motion.p>
        </div>

        {/* ── 2-column feature grid ───────────────────────────────────────
            Outer border-2 frames the grid.
            gap-px + bg-ink bleeds 1px ink lines between all 4 cells.       */}
        <div className="border-x-2 border-b-2 border-ink">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-ink">
            {FEATURES.map((f) => (
              <FeatureCard key={f.tag} {...f} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
