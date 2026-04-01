import { motion } from "framer-motion";
import { Zap, Database, Cpu, Globe, Share2, Layers } from "lucide-react";
import Pulsar from "../ui/Pulsar";

// Connecting Line Component (Print Style)
const ConnectionLine = ({ x1, y1, x2, y2, delay = 0 }: any) => (
  <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
    <motion.line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke="var(--color-ink)"
      strokeWidth="1.5"
      strokeDasharray="4,8"
      initial={{ strokeDashoffset: 0, opacity: 0 }}
      whileInView={{ opacity: 1 }}
      animate={{ strokeDashoffset: -100 }}
      transition={{
        strokeDashoffset: {
          duration: 10,
          repeat: Infinity,
          ease: "linear",
          delay,
        },
        opacity: { duration: 0.1 },
      }}
    />
  </svg>
);

const Node = ({ icon: Icon, title, desc, delay = 0, className = "" }: any) => (
  <div
    className={`relative z-10 p-4 border-2 border-ink bg-paper flex flex-col items-center text-center w-48 transition-all duration-300 group hover:bg-clay hover:border-clay hover:text-paper ${className}`}
  >
    <div className="w-10 h-10 border border-ink bg-paper flex items-center justify-center mb-3 group-hover:border-paper group-hover:bg-nautical transition-all duration-300">
      <Icon size={18} className="text-ink group-hover:text-paper" />
    </div>
    <h4 className="text-[10px] font-bold font-mono text-ink mb-1 uppercase tracking-widest px-2 border-b border-ink pb-1 group-hover:text-paper group-hover:border-paper">
      {title}
    </h4>
    <p className="text-[9px] font-mono text-ink leading-tight uppercase mt-1 group-hover:text-paper/80">{desc}</p>
  </div>
);

export default function Architecture() {
  return (
    <section className="relative w-full py-40 border-b-4 border-ink bg-paper font-sans">
      <div className="container mx-auto px-6 max-w-7xl relative">
        <div className="text-center mb-28 border-b-2 border-ink pb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-6 bg-paper">
            <Share2 size={14} className="text-ink" />
            <span className="text-xs font-semibold tracking-widest uppercase text-ink font-mono font-bold">
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
            We focus on orchestration. Specialized agents handle retrieval, ranking, and synthesis to compile persistent intelligence for modern developers.
          </p>
        </div>

        {/* The Diagram */}
        <div className="relative w-full h-[600px] flex items-center justify-center">
          
          {/* Central Node - Pulsar */}
          <div className="relative z-20">
            <Pulsar size={240} color="ink" />
          </div>

          {/* Satellite Nodes */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2">
            <Node
              title="Sourcing_Agent"
              desc="Scraping ArXiv & Repos"
              icon={Globe}
              delay={0}
            />
            <ConnectionLine x1="50%" y1="100%" x2="50%" y2="240" delay={0} />
          </div>

          <div className="absolute bottom-0 left-1/2 -translate-x-1/2">
            <Node
              title="Delivery_Node"
              desc="Cached Print Sync"
              icon={Layers}
              delay={0}
            />
            <ConnectionLine x1="50%" y1="-100%" x2="50%" y2="360" delay={0} />
          </div>

          <div className="absolute top-1/2 left-0 -translate-y-1/2 hidden md:block">
            <Node
              title="Vector_DB"
              desc="High-Dim Embeddings"
              icon={Database}
              delay={0}
            />
            <ConnectionLine x1="100%" y1="50%" x2="380" y2="50%" delay={0} />
          </div>

          <div className="absolute top-1/2 right-0 -translate-y-1/2 hidden md:block">
            <Node
              title="Synthesis_LLM"
              desc="Agentic Reasoners"
              icon={Cpu}
              delay={0}
            />
            <ConnectionLine x1="-100%" y1="50%" x2="600" y2="50%" delay={0} />
          </div>
          
        </div>

      </div>
    </section>
  );
}
