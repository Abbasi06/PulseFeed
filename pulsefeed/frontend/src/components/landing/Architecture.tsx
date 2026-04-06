import { motion } from "framer-motion";
import { Database, Cpu, Globe, Layers, Share2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Pulsar from "../ui/Pulsar";

// ── Types ──────────────────────────────────────────────────────────────────

interface NodeData {
  icon: LucideIcon;
  title: string;
  desc: string;
}

// ── Data ───────────────────────────────────────────────────────────────────

const NODES: NodeData[] = [
  { icon: Globe, title: "Sourcing_Agent", desc: "Scraping ArXiv & Repos" },
  { icon: Database, title: "Vector_DB", desc: "High-Dim Embeddings" },
  { icon: Cpu, title: "Synthesis_LLM", desc: "Agentic Reasoners" },
  { icon: Layers, title: "Delivery_Node", desc: "Cached Print Sync" },
];

// ── Node card ──────────────────────────────────────────────────────────────

function NodeCard({
  icon: Icon,
  title,
  desc,
  className = "",
}: NodeData & { className?: string }) {
  return (
    <div
      className={`p-4 border-2 border-ink bg-paper flex flex-col items-center text-center
                  transition-all duration-300 group
                  hover:bg-clay hover:border-clay hover:text-paper ${className}`}
    >
      <div
        className="w-10 h-10 border border-ink bg-paper flex items-center justify-center mb-3
                      group-hover:border-paper group-hover:bg-paper/20 transition-all duration-300"
      >
        <Icon size={18} className="text-ink group-hover:text-paper" />
      </div>
      <h4
        className="text-[10px] font-bold font-mono text-ink mb-1 uppercase tracking-widest
                     px-2 border-b border-ink pb-1 w-full
                     group-hover:text-paper group-hover:border-paper"
      >
        {title}
      </h4>
      <p className="text-[9px] font-mono text-ink leading-tight uppercase mt-1 group-hover:text-paper/80">
        {desc}
      </p>
    </div>
  );
}

// ── Animated SVG connection lines ──────────────────────────────────────────
// Uses percentage coordinates + vector-effect="non-scaling-stroke" so the
// stroke width stays 1px regardless of the container's aspect ratio.

function DiagramLines() {
  const lineProps = {
    stroke: "var(--color-ink)",
    strokeWidth: 1,
    strokeDasharray: "4 8",
    strokeOpacity: 0.4,
    // @ts-ignore — valid SVG presentation attribute, not in React types
    vectorEffect: "non-scaling-stroke",
  };

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      // percentage-based coordinates — lines are horizontal/vertical so
      // preserveAspectRatio="none" stretch doesn't distort their appearance
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
    >
      {/* Center → Top */}
      <motion.line
        x1="50%"
        y1="50%"
        x2="50%"
        y2="12%"
        {...lineProps}
        animate={{ strokeDashoffset: [0, -48] }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      />
      {/* Center → Left */}
      <motion.line
        x1="50%"
        y1="50%"
        x2="12%"
        y2="50%"
        {...lineProps}
        animate={{ strokeDashoffset: [0, -48] }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "linear",
          delay: 0.5,
        }}
      />
      {/* Center → Right */}
      <motion.line
        x1="50%"
        y1="50%"
        x2="88%"
        y2="50%"
        {...lineProps}
        animate={{ strokeDashoffset: [0, -48] }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear", delay: 1 }}
      />
      {/* Center → Bottom */}
      <motion.line
        x1="50%"
        y1="50%"
        x2="50%"
        y2="88%"
        {...lineProps}
        animate={{ strokeDashoffset: [0, -48] }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "linear",
          delay: 1.5,
        }}
      />
    </svg>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function Architecture() {
  return (
    <section
      id="architecture"
      className="relative z-10 w-full py-40 border-b-4 border-ink bg-paper font-sans"
    >
      <div className="max-w-6xl mx-auto px-4 md:px-8 relative">
        {/* Section header */}
        <div className="text-center mb-20 border-b-2 border-ink pb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-6 bg-paper">
            <Share2 size={14} className="text-ink" />
            <span className="text-xs font-mono font-bold tracking-widest uppercase text-ink">
              [/] System Topography
            </span>
          </div>
          <h2 className="text-5xl md:text-7xl font-bold font-display text-ink tracking-tighter leading-[0.9] uppercase">
            A Multi-Agent <br />
            <span className="text-clay italic font-display">
              Swarm Architecture.
            </span>
          </h2>
          <p className="font-mono text-xs uppercase tracking-widest text-ink mt-8 max-w-xl mx-auto border-t border-ink pt-6">
            We focus on orchestration. Specialized agents handle retrieval,
            ranking, and synthesis to compile persistent intelligence for modern
            developers.
          </p>
        </div>

        {/* ── MOBILE: 2×2 card grid ──────────────────────────────────────
            gap-px + bg-ink creates 1px ink borders between cells.          */}
        <div className="grid grid-cols-2 gap-px bg-ink border-2 border-ink lg:hidden">
          {NODES.map((node) => (
            <div
              key={node.title}
              className="bg-paper flex items-center justify-center p-8"
            >
              <NodeCard {...node} className="w-full max-w-[200px]" />
            </div>
          ))}
        </div>

        {/* ── DESKTOP: Radial diagram ─────────────────────────────────────
            Nodes are pinned to cardinal edges with CSS absolute positioning.
            SVG overlay draws animated dashed connection lines.              */}
        <div className="relative hidden lg:flex items-center justify-center w-full h-[560px]">
          <DiagramLines />

          {/* Center: Pulsar — covers the SVG line intersection */}
          <div className="relative z-20">
            <Pulsar size={220} color="ink" />
          </div>

          {/* Top: Sourcing_Agent */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10">
            <NodeCard {...NODES[0]} className="w-44" />
          </div>

          {/* Left: Vector_DB */}
          <div className="absolute left-0 top-1/2 -translate-y-1/2 z-10">
            <NodeCard {...NODES[1]} className="w-44" />
          </div>

          {/* Right: Synthesis_LLM */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 z-10">
            <NodeCard {...NODES[2]} className="w-44" />
          </div>

          {/* Bottom: Delivery_Node */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 z-10">
            <NodeCard {...NODES[3]} className="w-44" />
          </div>
        </div>
      </div>
    </section>
  );
}
