import { motion, useInView } from "framer-motion";
import { Database, Cpu, Globe, Layers, Share2, ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useRef } from "react";

interface NodeData {
  icon: LucideIcon;
  title: string;
  desc: string;
  tag: string;
  delay: number;
}

const NODES: NodeData[] = [
  {
    icon: Globe,
    title: "Sourcing_Agent",
    desc: "Scrapes ArXiv, GitHub repos, and technical blogs in real time.",
    tag: "LAYER.01",
    delay: 0,
  },
  {
    icon: Database,
    title: "Vector_DB",
    desc: "High-dimensional embeddings for semantic deduplication and ranking.",
    tag: "LAYER.02",
    delay: 0.1,
  },
  {
    icon: Cpu,
    title: "Synthesis_LLM",
    desc: "Agentic reasoner distilling raw content into 3-sentence briefs.",
    tag: "LAYER.03",
    delay: 0.2,
  },
  {
    icon: Layers,
    title: "Delivery_Node",
    desc: "Pre-computed context synced across devices with zero cold-starts.",
    tag: "LAYER.04",
    delay: 0.3,
  },
];

// ── Flow step card ─────────────────────────────────────────────────────────

function FlowCard({
  icon: Icon,
  title,
  desc,
  tag,
  delay,
  index,
}: NodeData & { index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 32 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className="relative flex flex-col gap-4 p-8 bg-paper border-2 border-ink group hover:bg-ink transition-none"
    >
      {/* Tag */}
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-clay">
          {tag}
        </span>
        <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-ink/30 group-hover:text-paper/30">
          {String(index + 1).padStart(2, "0")}
        </span>
      </div>

      {/* Icon */}
      <div className="w-12 h-12 border-2 border-ink flex items-center justify-center group-hover:border-paper group-hover:bg-paper/10 transition-none">
        <Icon size={20} className="text-ink group-hover:text-paper" />
      </div>

      {/* Text */}
      <div>
        <h4 className="font-mono font-bold text-sm uppercase tracking-widest text-ink group-hover:text-paper mb-2">
          {title}
        </h4>
        <p className="font-sans text-[13px] text-ink/60 group-hover:text-paper/60 leading-relaxed">
          {desc}
        </p>
      </div>

      {/* Bottom pulse indicator */}
      <div
        className="mt-auto pt-4 flex items-center gap-2"
        style={{ borderTop: "1px solid rgba(35,31,32,0.15)" }}
      >
        <motion.div
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 2, repeat: Infinity, delay: index * 0.5 }}
          className="w-1.5 h-1.5 rounded-full bg-clay"
        />
        <span className="text-[9px] font-mono uppercase tracking-widest text-ink/30 group-hover:text-paper/30">
          Active
        </span>
      </div>
    </motion.div>
  );
}

// ── Animated SVG pipeline ──────────────────────────────────────────────────

function PipelineFlow() {
  return (
    <div className="relative w-full overflow-hidden py-10 border-y-2 border-ink bg-paper">
      {/* Pipeline line */}
      <div className="relative max-w-4xl mx-auto px-8">
        <div className="flex items-center">
          {NODES.map((node, i) => {
            const Icon = node.icon;
            return (
              <div
                key={node.tag}
                className="flex items-center flex-1 last:flex-none"
              >
                {/* Node circle */}
                <motion.div
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{
                    duration: 0.4,
                    delay: i * 0.15,
                    type: "spring",
                    stiffness: 300,
                  }}
                  className="relative shrink-0 w-14 h-14 border-2 border-ink bg-paper flex items-center justify-center z-10"
                >
                  <Icon size={18} className="text-ink" />
                  {/* Pulsing ring */}
                  <motion.div
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{
                      duration: 2.5,
                      repeat: Infinity,
                      delay: i * 0.6,
                    }}
                    className="absolute inset-0 border border-clay pointer-events-none"
                  />
                </motion.div>

                {/* Connector arrow */}
                {i < NODES.length - 1 && (
                  <div className="flex-1 flex items-center px-2 overflow-hidden">
                    <div className="w-full h-px bg-ink/20 relative">
                      {/* Travelling dot */}
                      <motion.div
                        animate={{ x: ["-100%", "200%"] }}
                        transition={{
                          duration: 1.8,
                          repeat: Infinity,
                          delay: i * 0.4,
                          ease: "linear",
                        }}
                        className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
                        style={{ background: "var(--color-clay)" }}
                      />
                    </div>
                    <ArrowRight
                      size={10}
                      className="text-ink/30 shrink-0 -ml-1"
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Labels below */}
        <div className="flex mt-4">
          {NODES.map((node, i) => (
            <div
              key={node.tag}
              className="flex-1 last:flex-none flex justify-center"
              style={{ maxWidth: i < NODES.length - 1 ? undefined : "56px" }}
            >
              <span className="text-[9px] font-mono uppercase tracking-widest text-ink/40 text-center">
                {node.title.replace("_", " ")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main section ───────────────────────────────────────────────────────────

export default function Architecture() {
  return (
    <section
      id="architecture"
      className="relative z-10 w-full border-b-4 border-ink bg-paper font-sans"
    >
      {/* Section header */}
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-20 md:py-24 border-b-2 border-ink">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-6 bg-paper">
              <Share2 size={14} className="text-ink" />
              <span className="text-xs font-mono font-bold tracking-widest uppercase text-ink">
                [/] System Topography
              </span>
            </div>
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-display font-bold text-ink tracking-tighter leading-[0.9] uppercase">
              A Multi-Agent <br />
              <span className="italic text-clay">Swarm Architecture.</span>
            </h2>
          </div>
          <p className="font-mono text-xs uppercase tracking-widest text-ink/50 md:text-right max-w-sm md:ml-auto leading-relaxed border-l-2 md:border-l-0 md:border-r-2 border-ink pl-4 md:pl-0 md:pr-4">
            Specialized agents handle retrieval, ranking, and synthesis in a
            continuous pipeline — compiling persistent intelligence while you
            build.
          </p>
        </div>
      </div>

      {/* Animated pipeline flow diagram */}
      <PipelineFlow />

      {/* 4-card grid */}
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-0">
        <div className="border-x-2 border-b-2 border-ink">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-ink">
            {NODES.map((node, i) => (
              <FlowCard key={node.tag} {...node} index={i} />
            ))}
          </div>
        </div>
      </div>

      {/* Bottom stat strip */}
      <div className="max-w-6xl mx-auto px-4 md:px-8">
        <div className="border-x-2 border-b-2 border-ink grid grid-cols-3 divide-x-2 divide-ink">
          {[
            { value: "< 200ms", label: "Synthesis latency" },
            { value: "4 agents", label: "Concurrent pipeline" },
            { value: "100%", label: "Personalized output" },
          ].map((s) => (
            <div key={s.label} className="px-6 py-5 text-center">
              <div className="text-2xl md:text-3xl font-display font-bold text-clay tracking-tighter">
                {s.value}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-ink/40 mt-1">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
