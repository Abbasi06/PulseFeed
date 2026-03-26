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

// Trace Line Component
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
        stroke="url(#traceGrad)"
        strokeWidth="1"
        strokeDasharray="5,10"
        animate={{ strokeDashoffset: [0, -100] }}
        transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
      />
      <defs>
        <linearGradient id="traceGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#B7397A" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#4C6E94" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  </div>
);

// Live Terminal Snippet
const LiveTerminal = () => (
  <div className="mt-8 w-full max-w-md rounded-xl bg-black/60 border border-white/5 p-4 font-mono text-[10px] shadow-2xl overflow-hidden h-32 relative">
    <div className="flex gap-1.5 mb-3 border-b border-white/5 pb-2">
      <div className="w-2 h-2 rounded-full bg-red-500/50" />
      <div className="w-2 h-2 rounded-full bg-yellow-500/50" />
      <div className="w-2 h-2 rounded-full bg-green-500/50" />
      <span className="ml-2 text-white/20 uppercase tracking-[2px]">
        Swarm_Monitor.sh
      </span>
    </div>
    <div className="space-y-1 text-white/40">
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 0.2 }}>
        [09:44:01] <span className="text-[#B7397A]">SWARM_INIT</span>: Listening
        on Port 8080
      </motion.p>
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 0.8 }}>
        [09:44:12] <span className="text-blue-400">INGEST_ARXIV</span>:
        [arXiv:2403.00123] - 100%
      </motion.p>
      <motion.p animate={{ opacity: [0, 1] }} transition={{ delay: 1.4 }}>
        [09:44:15] <span className="text-green-400">SYNTHESIS</span>: Extracting
        high-signal entities...
      </motion.p>
      <motion.p
        animate={{ opacity: [0, 1] }}
        transition={{ repeat: Infinity, repeatDelay: 5 }}
      >
        [09:44:18] <span className="text-yellow-400">MATCH</span>: Found 12
        GitHub repos for 'KV-Cache'
      </motion.p>
    </div>
    <div className="absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-black to-transparent" />
  </div>
);

// Orbiting icon component
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
        <div className="absolute inset-0 bg-white/20 blur-md rounded-full scale-0 group-hover:scale-150 transition-transform duration-500" />
        <div className="relative flex items-center justify-center w-10 h-10 rounded-full bg-[#1c1b24] border border-white/10 text-white/50 group-hover:text-white group-hover:border-white/30 transition-all duration-300">
          <Icon size={18} />
          <span className="absolute top-12 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] uppercase tracking-widest text-white/30 group-hover:text-white/60 transition-colors opacity-0 group-hover:opacity-100 font-bold">
            {label}
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default function WhyUs() {
  return (
    <section className="relative w-full py-48 bg-[#010101] font-sans selection:bg-[#B7397A]/30 border-t border-white/5">
      <div className="container mx-auto px-6 max-w-5xl">
        {/* Section Head */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-6"
          >
            <ShieldCheck size={14} className="text-[#B7397A]" />
            <span className="text-xs font-semibold tracking-widest uppercase text-white/30 font-bold">
              Dual-Brain Architecture
            </span>
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.8 }}
            className="text-4xl md:text-5xl lg:text-7xl font-bold text-white tracking-tighter leading-[0.9]"
          >
            High-Performance <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
              Intelligence Substrate.
            </span>
          </motion.h2>
        </div>

        {/* Large Top Card */}
        <motion.div
          initial={{ opacity: 0, y: 60, scale: 0.98 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          className="relative group p-12 rounded-[3.5rem] bg-[rgba(28,27,36,0.25)] border border-white/10 hover:border-white/20 transition-all duration-700 overflow-hidden backdrop-blur-3xl mb-8 flex flex-col items-center text-center shadow-[0_40px_100px_rgba(0,0,0,0.5)]"
        >
          <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />

          <h3 className="relative z-10 text-2xl font-bold text-white mb-4 tracking-tight">
            Continuous Sourcing & Vectorization
          </h3>
          <p className="relative z-10 text-white/40 max-w-2xl mb-12 leading-relaxed text-sm">
            PulseFeed's inference engine operates at the intersection of
            retrieval and reasoning, extracting signal from raw technical
            firehoses to build a persistent context graph.
          </p>

          {/* Animation Area */}
          <div className="relative w-full h-[320px] flex items-center justify-center">
            {/* Trace Lines */}
            {[0, 60, 120, 180, 240, 300].map((r) => (
              <TraceLine key={r} rotate={r} />
            ))}

            {/* Center Core */}
            <div className="relative z-20 w-28 h-28 rounded-full bg-gradient-to-br from-[#B7397A] to-[#4C6E94] flex items-center justify-center p-0.5 shadow-[0_0_80px_rgba(183,57,122,0.4)]">
              <div className="w-full h-full rounded-full bg-black/60 backdrop-blur-xl flex items-center justify-center overflow-hidden border border-white/10">
                <motion.div
                  animate={{
                    scale: [1, 1.3, 1],
                    opacity: [0.3, 0.7, 0.3],
                  }}
                  transition={{ duration: 3, repeat: Infinity }}
                  className="absolute inset-0 bg-white/20 blur-2xl"
                />
                <Database size={40} className="text-white relative z-10" />
              </div>
            </div>

            {/* Orbiting Paths */}
            <div className="absolute w-[240px] h-[100px] border border-white/10 rounded-[100%] rotate-[-15deg] opacity-20" />
            <div className="absolute w-[320px] h-[140px] border border-white/10 rounded-[100%] rotate-[10deg] opacity-20" />

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

          <LiveTerminal />
        </motion.div>

        {/* Two Small Cards Below */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="p-12 rounded-[3rem] bg-[rgba(28,27,36,0.3)] border border-white/10 hover:border-white/25 transition-all duration-700 overflow-hidden backdrop-blur-3xl flex flex-col items-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-8 shadow-2xl">
              <Zap size={24} className="text-[#B7397A]" />
            </div>
            <h4 className="text-xl font-bold text-white mb-4">
              Zero-Latency Synthesis
            </h4>
            <p className="text-white/40 text-[13px] leading-relaxed text-center">
              Our Inference Cascade pre-computes context before you request it,
              ensuring 10X faster knowledge retrieval with zero cold-starts.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="p-12 rounded-[3rem] bg-[rgba(28,27,36,0.3)] border border-white/10 hover:border-white/25 transition-all duration-700 overflow-hidden backdrop-blur-3xl flex flex-col items-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-8 shadow-2xl">
              <Globe size={24} className="text-[#4C6E94]" />
            </div>
            <h4 className="text-xl font-bold text-white mb-4">
              Hyper-Personalized Filters
            </h4>
            <p className="text-white/40 text-[13px] leading-relaxed text-center">
              Beyond keywords. Our swarm uses Contextual Bandits to map your
              evolving technical sub-interests and strip away SEO fluff.
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
