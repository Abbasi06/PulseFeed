import { motion } from "framer-motion";
import {
  UserPlus,
  Zap,
  Terminal,
  Laptop,
  Smartphone,
  Search,
  CheckCircle2,
  Navigation,
  Layers,
  Filter,
} from "lucide-react";

// Step 1 UI: Context Sync
const ContextSyncUI = () => (
  <div className="relative w-full h-full p-4 flex flex-col gap-3">
    <div className="flex items-center justify-between border-b border-white/5 pb-2">
      <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest">
        Context_Sync.v1
      </span>
      <div className="flex gap-1">
        <div className="w-1.5 h-1.5 rounded-full bg-[#B7397A] animate-pulse" />
        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
      </div>
    </div>
    <div className="flex flex-wrap gap-2">
      {["vLLM", "RAG", "KEDA", "Nvidia", "PyTorch"].map((t, i) => (
        <motion.div
          key={i}
          animate={{
            backgroundColor:
              i < 3 ? "rgba(183, 57, 122, 0.2)" : "rgba(255, 255, 255, 0.05)",
            borderColor:
              i < 3 ? "rgba(183, 57, 122, 0.4)" : "rgba(255, 255, 255, 0.1)",
          }}
          className="px-2 py-1 rounded-md border text-[9px] text-white/60 font-mono"
        >
          {t}
        </motion.div>
      ))}
    </div>
    <div className="mt-auto flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
      <Search size={10} className="text-white/40" />
      <div className="h-1 bg-white/10 flex-1 rounded-full overflow-hidden">
        <motion.div
          animate={{ x: [-50, 100] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="h-full w-1/3 bg-[#B7397A]"
        />
      </div>
    </div>
  </div>
);

// Step 2 UI: Quality Gate
const QualityGateUI = () => (
  <div className="relative w-full h-full p-4 flex flex-col justify-center items-center">
    <div className="absolute top-4 left-4 text-[9px] font-mono text-white/30 uppercase">
      Noise_Reduction_Engine
    </div>
    <div className="relative w-32 h-32 flex items-center justify-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        className="absolute inset-0 rounded-full border border-dashed border-white/10"
      />
      <div className="relative z-10 flex flex-col items-center">
        <Filter size={24} className="text-[#B7397A] mb-2" />
        <span className="text-xl font-bold text-white">85%</span>
        <span className="text-[8px] text-white/40 uppercase font-bold">
          Noise Stripped
        </span>
      </div>
      {/* Pulsing rings */}
      <motion.div
        animate={{ scale: [1, 1.5, 1], opacity: [0.1, 0, 0.1] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="absolute inset-0 rounded-full border border-[#B7397A]/20"
      />
    </div>
  </div>
);

// Step 3 UI: Synthesized Intelligence
const SynthesisUI = () => (
  <div className="relative w-full h-full p-4 flex flex-col gap-3">
    <div className="flex items-center gap-2 mb-1">
      <div className="px-2 py-0.5 rounded bg-[#4C6E94]/20 border border-[#4C6E94]/40 text-[8px] text-[#4C6E94] font-bold">
        SYNTHESIS_REPORT
      </div>
      <div className="h-px flex-1 bg-white/5" />
    </div>
    <div className="p-3 rounded-xl bg-white/5 border border-white/10 space-y-2">
      <div className="flex justify-between items-start">
        <h5 className="text-[11px] font-bold text-white leading-tight">
          Quantization vs LoRA: A Performance Benchmark
        </h5>
        <CheckCircle2 size={10} className="text-green-500 shrink-0" />
      </div>
      <div className="space-y-1">
        <div className="h-1 w-full bg-white/10 rounded-full" />
        <div className="h-1 w-3/4 bg-white/10 rounded-full" />
        <div className="h-1 w-1/2 bg-white/5 rounded-full" />
      </div>
    </div>
    <div className="flex justify-between items-center mt-auto">
      <div className="flex -space-x-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="w-5 h-5 rounded-full bg-white/10 border border-black shadow-xl"
          />
        ))}
      </div>
      <button className="px-3 py-1 rounded bg-[#B7397A] text-white text-[9px] font-bold hover:bg-[#B7397A]/80 transition-colors">
        Read Brief
      </button>
    </div>
  </div>
);

// Step 4 UI: Global Flow
const GlobalFlowUI = () => (
  <div className="relative w-full h-full flex flex-col items-center justify-center p-4">
    <div className="relative flex items-center gap-8">
      <div className="flex flex-col items-center gap-2">
        <Smartphone size={32} className="text-white/20" />
        <div className="w-8 h-12 rounded-md bg-white/5 border border-white/10 p-1">
          <div className="h-1 w-full bg-[#B7397A]/40 rounded-full" />
        </div>
      </div>
      <div className="relative">
        <motion.div
          animate={{ x: [-20, 20] }}
          transition={{ duration: 3, repeat: Infinity, repeatType: "reverse" }}
          className="flex items-center"
        >
          <Zap size={16} className="text-[#B7397A]" />
          <div className="w-12 h-px bg-gradient-to-r from-[#B7397A] to-transparent" />
        </motion.div>
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] font-mono text-white/20">
          SYNC_PASS
        </div>
      </div>
      <div className="flex flex-col items-center gap-2">
        <Laptop size={32} className="text-white/20" />
        <div className="w-12 h-8 rounded-md bg-white/5 border border-white/10 p-1">
          <div className="h-1 w-full bg-[#4C6E94]/40 rounded-full" />
        </div>
      </div>
    </div>
  </div>
);

const steps = [
  {
    number: "01",
    title: "Initialize Your Swarm",
    description:
      "Define your technical context. Our multi-agent swarm maps your sub-interests across 100+ daily data sources.",
    visual: ContextSyncUI,
    tag: "Context_Engine",
  },
  {
    number: "02",
    title: "Autonomous Filtering",
    description:
      "The 'Quality Gate' analyzes content for depth and technical merit—stripping away SEO bait and marketing fluff.",
    visual: QualityGateUI,
    tag: "Signal_Processor",
  },
  {
    number: "03",
    title: "Intelligence Synthesis",
    description:
      "Complex papers and repos are distilled into hyper-personalized briefs. We synthesize signal, not just links.",
    visual: SynthesisUI,
    tag: "RAG_Synthesizer",
  },
  {
    number: "04",
    title: "Cross-Platform Delivery",
    description:
      "Your technical context follows you. Pre-computed and cached for zero-latency access across all your devices.",
    visual: GlobalFlowUI,
    tag: "Edge_Sync",
  },
];

export default function HowItWorks() {
  return (
    <section
      id="process"
      className="relative w-full py-48 bg-[#010101] font-sans selection:bg-[#B7397A]/30 border-t border-white/5"
    >
      <div className="container mx-auto px-6 max-w-6xl">
        {/* Section Head */}
        <div className="text-center mb-24">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-6"
          >
            <Layers size={14} className="text-[#B7397A]" />
            <span className="text-xs font-semibold tracking-widest uppercase text-white/30 font-bold">
              Operational Pipeline
            </span>
          </motion.div>
          <motion.h2
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.8 }}
            className="text-4xl md:text-5xl lg:text-7xl font-bold text-white tracking-tighter leading-[0.9]"
          >
            From Firehose <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
              to Direct Intelligence.
            </span>
          </motion.h2>
        </div>

        {/* 2x2 Numbered Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 60, scale: 0.98 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{
                delay: i * 0.1,
                duration: 0.8,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="group relative p-10 rounded-[3.5rem] bg-[rgba(28,27,36,0.25)] border border-white/10 hover:border-white/20 transition-all duration-500 overflow-hidden backdrop-blur-3xl flex flex-col shadow-[0_30px_80px_rgba(0,0,0,0.4)]"
            >
              {/* Inner Glow */}
              <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />

              {/* Visual Area */}
              <div className="relative w-full h-[220px] mb-8 overflow-hidden rounded-3xl bg-black/40 border border-white/5 group-hover:border-white/10 transition-colors shadow-inner">
                <step.visual />

                {/* Step Number Overlay */}
                <span className="absolute top-4 right-6 text-[80px] font-bold text-white/5 select-none pointer-events-none tracking-tighter">
                  {step.number}
                </span>
              </div>

              {/* Text Content */}
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[10px] font-mono text-[#B7397A] font-bold tracking-widest">
                    {step.tag}
                  </span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-4 tracking-tight">
                  {step.title}
                </h3>
                <p className="text-white/40 text-[13px] leading-relaxed">
                  {step.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
