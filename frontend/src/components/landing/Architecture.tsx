import { motion } from "framer-motion";
import { Zap, Database, Cpu, Globe, Share2, Layers } from "lucide-react";

// Connecting Line Component
const ConnectionLine = ({ x1, y1, x2, y2, delay = 0 }: any) => (
  <svg className="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
    <motion.line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke="url(#lineGrad)"
      strokeWidth="1.5"
      strokeDasharray="4,8"
      initial={{ strokeDashoffset: 0, opacity: 0 }}
      whileInView={{ opacity: 0.3 }}
      animate={{ strokeDashoffset: -100 }}
      transition={{
        strokeDashoffset: {
          duration: 10,
          repeat: Infinity,
          ease: "linear",
          delay,
        },
        opacity: { duration: 1 },
      }}
    />
    <defs>
      <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#B7397A" />
        <stop offset="100%" stopColor="#4C6E94" />
      </linearGradient>
    </defs>
  </svg>
);

const Node = ({ icon: Icon, title, desc, delay = 0, className = "" }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay, duration: 0.8 }}
    className={`relative z-10 p-6 rounded-2xl bg-[rgba(28,27,36,0.3)] border border-white/10 backdrop-blur-3xl flex flex-col items-center text-center w-48 shadow-2xl ${className}`}
  >
    <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center mb-3">
      <Icon size={18} className="text-white/70" />
    </div>
    <h4 className="text-xs font-bold text-white mb-1 uppercase tracking-tighter">
      {title}
    </h4>
    <p className="text-[9px] text-white/40 leading-tight">{desc}</p>
  </motion.div>
);

export default function Architecture() {
  return (
    <section className="relative w-full py-48 bg-[#010101] overflow-hidden font-sans border-t border-white/5">
      <div className="container mx-auto px-6 max-w-6xl relative">
        <div className="text-center mb-28">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-6"
          >
            <Share2 size={14} className="text-[#B7397A]" />
            <span className="text-xs font-semibold tracking-widest uppercase text-white/30 font-bold">
              System Flow
            </span>
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-4xl md:text-5xl lg:text-7xl font-bold text-white tracking-tighter leading-[0.9]"
          >
            A Multi-Agent <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
              Swarm Infrastructure.
            </span>
          </motion.h2>
        </div>

        {/* The Diagram */}
        <div className="relative w-full h-[500px] flex items-center justify-center">
          {/* Background Glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#B7397A]/5 blur-[120px] rounded-full pointer-events-none" />

          {/* Central Node */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 1 }}
            className="relative z-20 w-32 h-32 rounded-full bg-gradient-to-br from-[#B7397A] to-[#4C6E94] p-0.5 shadow-[0_0_100px_rgba(183,57,122,0.5)]"
          >
            <div className="w-full h-full rounded-full bg-[#010101] flex flex-col items-center justify-center border border-white/20">
              <Zap size={32} className="text-white mb-1" />
              <span className="text-[10px] font-bold text-white uppercase tracking-tighter">
                The Swarm
              </span>
            </div>
          </motion.div>

          {/* Satellite Nodes */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2">
            <Node
              title="Sourcing_Agent"
              desc="Scraping ArXiv, GitHub & Tech Blogs"
              icon={Globe}
              delay={0.2}
            />
            <ConnectionLine x1="50%" y1="100%" x2="50%" y2="200" delay={0.1} />
          </div>

          <div className="absolute bottom-0 left-1/2 -translate-x-1/2">
            <Node
              title="Delivery_Node"
              desc="Web & Mobile Cached Sync"
              icon={Layers}
              delay={0.8}
            />
            <ConnectionLine x1="50%" y1="-100%" x2="50%" y2="300" delay={0.7} />
          </div>

          <div className="absolute top-1/2 left-0 -translate-y-1/2">
            <Node
              title="Vector_DB"
              desc="High-Dimensional Embedding RAG"
              icon={Database}
              delay={0.4}
            />
            <ConnectionLine x1="100%" y1="50%" x2="400" y2="50%" delay={0.3} />
          </div>

          <div className="absolute top-1/2 right-0 -translate-y-1/2">
            <Node
              title="Synthesis_LLM"
              desc="Agentic Reasoners & Brief Gen"
              icon={Cpu}
              delay={0.6}
            />
            <ConnectionLine x1="-100%" y1="50%" x2="600" y2="50%" delay={0.5} />
          </div>

          {/* Central Pulsing Rings */}
          <motion.div
            animate={{ scale: [1, 2], opacity: [0.2, 0] }}
            transition={{ duration: 3, repeat: Infinity }}
            className="absolute z-0 w-32 h-32 rounded-full border border-[#B7397A]"
          />
          <motion.div
            animate={{ scale: [1, 2.5], opacity: [0.1, 0] }}
            transition={{ duration: 4, repeat: Infinity, delay: 1 }}
            className="absolute z-0 w-32 h-32 rounded-full border border-white/10"
          />
        </div>

        {/* Bottom Text Detail */}
        <div className="mt-28 text-center max-w-2xl mx-auto">
          <p className="text-white/40 text-sm leading-relaxed italic">
            "We focus on the orchestration of high-dimensional technical
            context. By coordinating specialized agents for retrieval, ranking,
            and synthesis, PulseFeed creates a persistent intelligence layer for
            the modern developer."
          </p>
        </div>
      </div>
    </section>
  );
}
