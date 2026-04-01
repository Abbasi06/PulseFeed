import { motion } from "framer-motion";
import {
  Database,
  Zap,
  Globe,
  FileText,
  Code,
  Search,
  ShieldCheck,
} from "lucide-react";

// Trace Line Component (Print)
const TraceLine = ({ rotate = 0 }: { rotate?: number }) => (
  <div
    className="absolute inset-0 flex items-center justify-center pointer-events-none"
    style={{ transform: `rotate(${rotate}deg)` }}
  >
    <svg width="400" height="400" className="overflow-visible">
      <motion.line
        x1="200"
        y1="200"
        x2="350"
        y2="200"
        stroke="var(--color-ink)"
        strokeWidth="1"
        strokeDasharray="4,8"
        animate={{ strokeDashoffset: [0, -100] }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
      />
    </svg>
  </div>
);

// Live Terminal Snippet (Print)
const LiveTerminal = () => (
  <div className="mt-12 w-full max-w-xl mx-auto border-2 border-ink bg-paper font-mono text-xs overflow-hidden">
    <div className="flex justify-between items-center mb-0 border-b-2 border-ink p-3 bg-ink text-paper">
      <span className="font-bold tracking-[2px] uppercase">
        Monitor // Swarm_Init
      </span>
      <div className="flex gap-2">
         <div className="w-2 h-2 border border-paper bg-transparent" />
         <div className="w-2 h-2 border border-paper bg-transparent" />
         <div className="w-2 h-2 border border-paper bg-paper" />
      </div>
    </div>
    <div className="p-4 space-y-2 text-ink">
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 0.2 }}>
        <span className="font-bold">[09:44:01] SWARM_INIT</span>: Binding to port 8080...
      </motion.p>
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 0.8 }}>
        <span className="font-bold">[09:44:12] INGEST_ARXIV</span>: Extracting [arXiv:2403.00123]
      </motion.p>
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 1.4 }}>
        <span className="font-bold text-clay">[09:44:15] SYNTHESIS</span>: Validating high-signal entities.
      </motion.p>
      <motion.p
        animate={{ opacity: [0, 1] }}
        transition={{ repeat: Infinity, repeatDelay: 5 }}
      >
        <span className="font-bold">[09:44:18] ALIGN</span>: 12 GitHub repos mapped for 'KV-Cache'.
      </motion.p>
    </div>
  </div>
);

// Orbiting icon component (Print)
const OrbitingIcon = ({
  delay = 0,
  radius = 80,
  duration = 10,
  icon: Icon,
  label,
}: any) => {
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration, repeat: Infinity, ease: "linear", delay }}
      style={{
        position: "absolute",
        width: radius * 2,
        height: radius * 2,
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration, repeat: Infinity, ease: "linear", delay }}
        className="relative group pointer-events-auto"
      >
        <div className="relative flex items-center justify-center w-10 h-10 border-2 border-ink rounded-none bg-paper text-ink transition-all duration-300 group-hover:bg-clay group-hover:text-paper group-hover:border-clay">
          <Icon size={16} />
          <span className="absolute top-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] uppercase font-mono font-bold tracking-widest text-ink bg-paper border border-ink px-1 opacity-0 group-hover:opacity-100 transition-all duration-300 z-10 block">
            {label}
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default function WhyUs() {
  return (
    <section className="relative w-full py-32 bg-paper font-sans selection:bg-clay selection:text-paper border-b-4 border-ink">
      <div className="container mx-auto px-6 max-w-7xl">
        {/* Section Head */}
        <div className="text-center mb-20 border-b-2 border-ink pb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 border-2 border-ink mb-6 bg-paper">
            <ShieldCheck size={14} className="text-ink" />
            <span className="text-xs font-mono font-bold tracking-widest uppercase text-ink">
              [/] Dual-Brain Architecture
            </span>
          </div>
          <h2 className="text-5xl md:text-7xl font-display font-bold text-ink tracking-tighter leading-[0.9] uppercase">
            High-Performance <br />
            <span className="italic text-clay font-display">
              Intelligence Substrate.
            </span>
          </h2>
        </div>

        {/* Large Top Card (Print) */}
        <div className="relative group border-2 border-ink bg-paper transition-all duration-300 overflow-hidden mb-8 flex flex-col items-center text-center">
          <div className="p-12 pb-0 relative z-10 w-full">
            <div className="text-xs font-mono font-bold uppercase tracking-widest text-ink border-b-2 border-ink pb-4 mb-6 text-left">
              [/] Component // Continuous Sourcing & Vectorization
            </div>
            <p className="font-mono text-sm text-ink max-w-2xl mx-auto leading-relaxed border-l-4 border-ink pl-4 text-left">
              The engine operates at the intersection of retrieval and reasoning. It extracts pure signal from raw firehoses to build a persistent context graph.
            </p>
          </div>

          {/* Animation Area */}
          <div className="relative w-full h-[400px] flex items-center justify-center mt-8 border-y-2 border-ink bg-[#F5F0E8] overflow-hidden">
            {/* Trace Lines */}
            {[0, 60, 120, 180, 240, 300].map((r) => (
              <TraceLine key={r} rotate={r} />
            ))}

            {/* Center Core */}
            <div className="relative z-20 w-32 h-32 border-4 border-ink rounded-full bg-paper flex items-center justify-center overflow-hidden">
                <div className="absolute inset-0 flex items-center justify-center opacity-10">
                   <div className="w-full h-[1px] bg-ink" />
                   <div className="h-full w-[1px] bg-ink absolute" />
                </div>
                <Database size={32} className="text-ink relative z-10" />
            </div>

            {/* Orbiting Paths */}
            <div className="absolute w-[240px] h-[100px] border border-ink rounded-[100%] rotate-[-15deg] opacity-30" />
            <div className="absolute w-[320px] h-[140px] border border-ink rounded-[100%] rotate-[10deg] opacity-30" />

            {/* Orbiting Icons */}
            <OrbitingIcon
              icon={Globe}
              radius={140}
              duration={18}
              delay={0}
              label="ArXiv"
            />
            <OrbitingIcon
              icon={Code}
              radius={180}
              duration={28}
              delay={-5}
              label="GitHub"
            />
            <OrbitingIcon
              icon={FileText}
              radius={160}
              duration={22}
              delay={-10}
              label="Logs"
            />
            <OrbitingIcon
              icon={Search}
              radius={120}
              duration={14}
              delay={-2}
              label="Deep Web"
            />
          </div>

          <div className="p-8 w-full bg-paper">
             <LiveTerminal />
          </div>
        </div>

        {/* Two Small Cards Below */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 border-t-2 border-ink pt-8">
          <div className="p-10 border-2 border-ink bg-paper flex flex-col items-center text-center hover:bg-ink hover:text-paper group transition-all duration-300 interactive-snap">
            <div className="w-16 h-16 border-2 border-ink rounded-none flex items-center justify-center mb-6 bg-paper text-ink transition-all duration-300">
              <Zap size={24} />
            </div>
            <h4 className="text-2xl font-display font-bold uppercase mb-4 tracking-tighter">
              Zero-Latency Synthesis
            </h4>
            <p className="font-mono text-xs leading-relaxed uppercase tracking-widest opacity-80">
              The cascade pre-computes context before requested—ensuring immediate retrieval with zero cold-starts.
            </p>
          </div>

          <div className="p-10 border-2 border-ink bg-paper flex flex-col items-center text-center hover:bg-ink hover:text-paper group transition-all duration-300 interactive-snap">
            <div className="w-16 h-16 border-2 border-ink rounded-none flex items-center justify-center mb-6 bg-paper text-ink transition-all duration-300">
              <Globe size={24} />
            </div>
            <h4 className="text-2xl font-display font-bold uppercase mb-4 tracking-tighter">
              Hyper-Personalized
            </h4>
            <p className="font-mono text-xs leading-relaxed uppercase tracking-widest opacity-80">
              Beyond keywords. The swarm maps evolving technical boundaries and strips away marketing noise.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
