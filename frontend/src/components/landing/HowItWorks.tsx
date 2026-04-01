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

// Step 1 UI: Context Sync (Print style)
const ContextSyncUI = () => (
  <div className="relative w-full h-full p-6 flex flex-col gap-4 bg-paper border-b-2 border-ink">
    <div className="flex items-center justify-between border-b-2 border-ink pb-2">
      <span className="text-[10px] font-bold text-ink uppercase font-mono tracking-widest">
        PROC.01 // CONTEXT_SYNC
      </span>
      <div className="flex gap-1">
        <div className="w-2 h-2 border border-ink bg-ink animate-pulse" />
        <div className="w-2 h-2 border border-ink" />
      </div>
    </div>
    <div className="flex flex-wrap gap-2">
      {["vLLM", "RAG", "KEDA", "Nvidia", "PyTorch"].map((t, i) => (
        <div
          key={i}
          className={`px-2 py-1 border text-[10px] font-bold font-mono uppercase ${
            i < 3 ? "bg-clay text-paper border-clay" : "bg-paper text-ink border-ink"
          }`}
        >
          {t}
        </div>
      ))}
    </div>
    <div className="mt-auto flex items-center gap-3 px-3 py-2 border-2 border-ink bg-paper">
      <Search size={12} className="text-ink" />
      <div className="h-2 border border-ink flex-1 p-[1px] bg-paper">
        <motion.div
          animate={{ x: [-50, 100] }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="h-full w-1/3 bg-ink"
        />
      </div>
    </div>
  </div>
);

// Step 2 UI: Quality Gate (Print style)
const QualityGateUI = () => (
  <div className="relative w-full h-full p-6 flex flex-col justify-center items-center bg-paper border-b-2 border-ink">
    <div className="absolute top-4 left-4 text-[10px] font-bold text-ink uppercase font-mono">
      PROC.02 // NOISE_FILTER
    </div>
    <div className="relative w-32 h-32 flex items-center justify-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        className="absolute inset-0 rounded-full border-2 border-dashed border-ink"
      />
      <div className="absolute inset-2 border border-ink rounded-full" />
      <div className="relative z-10 flex flex-col items-center p-4 bg-paper border-2 border-ink">
        <Filter size={20} className="text-ink mb-1" />
        <span className="text-xl font-display font-bold text-ink leading-none">85%</span>
        <span className="text-[8px] text-ink uppercase font-mono font-bold mt-1">
          Signal Purity
        </span>
      </div>
    </div>
  </div>
);

// Step 3 UI: Synthesized Intelligence (Print style)
const SynthesisUI = () => (
  <div className="relative w-full h-full p-6 flex flex-col gap-4 bg-paper border-b-2 border-ink">
    <div className="flex items-center justify-between border-b-2 border-ink pb-2">
      <span className="text-[10px] font-bold text-ink uppercase font-mono tracking-widest">
        PROC.03 // SYNTHESIS
      </span>
      <span className="px-2 py-0.5 border border-ink bg-ink text-paper text-[8px] font-mono font-bold uppercase">
        READY
      </span>
    </div>
    
    <div className="p-4 border-2 border-ink bg-paper space-y-4">
      <div className="flex justify-between items-start gap-4">
        <h5 className="text-sm font-bold font-display text-ink uppercase leading-tight">
          Quantization vs LoRA: A Benchmark
        </h5>
      </div>
      <div className="space-y-2">
        <div className="h-1.5 w-full bg-ink" />
        <div className="h-1.5 w-3/4 bg-ink" />
        <div className="h-1.5 w-1/2 bg-ink opacity-40" />
      </div>
    </div>
    
    <div className="flex justify-between items-center mt-auto pt-2">
      <div className="flex -space-x-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="w-6 h-6 rounded-none bg-paper border-2 border-ink"
          />
        ))}
      </div>
      <button className="px-3 py-1.5 border-2 border-ink bg-paper text-ink text-[10px] font-mono font-bold uppercase interactive-snap">
        [ READ_BRIEF ]
      </button>
    </div>
  </div>
);

// Step 4 UI: Global Flow (Print style)
const GlobalFlowUI = () => (
  <div className="relative w-full h-full flex flex-col items-center justify-center p-6 bg-paper border-b-2 border-ink">
    <div className="absolute top-4 left-4 text-[10px] font-bold text-ink uppercase font-mono">
      PROC.04 // DISTRIBUTION
    </div>
    <div className="relative flex items-center justify-between w-full max-w-[200px] gap-4">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-14 border-2 border-ink bg-paper p-1.5 flex flex-col gap-1">
          <div className="w-full h-2 bg-ink" />
          <div className="w-full flex-1 border border-ink" />
        </div>
      </div>
      
      <div className="relative flex-1 flex items-center justify-center">
        <motion.div
           className="w-full h-[2px] bg-ink overflow-hidden absolute"
        >
          <motion.div
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            className="w-1/2 h-full bg-clay"
          />
        </motion.div>
        <div className="bg-paper px-2 z-10">
           <Zap size={14} className="text-clay" />
        </div>
      </div>
      
      <div className="flex flex-col items-center gap-3">
        <div className="w-14 h-10 border-2 border-ink bg-paper p-1.5 flex gap-1">
          <div className="w-3 h-full bg-ink border border-ink" />
          <div className="flex-1 border border-ink" />
        </div>
      </div>
    </div>
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-[10px] font-mono font-bold text-clay tracking-widest uppercase bg-paper px-2">
      SYNCING_CACHE
    </div>
  </div>
);

const steps = [
  {
    number: "INIT",
    title: "Initialize Your Swarm",
    description: "Define your technical boundaries. Our multi-agent swarm maps your requirements across 100+ daily data sources, building a localized context graph.",
    visual: ContextSyncUI,
    tag: "MODULE.A",
  },
  {
    number: "EXEC",
    title: "Autonomous Filtering",
    description: "The 'Quality Gate' analyzes content for architectural depth and technical merit—stripping away SEO noise and corporate marketing fluff.",
    visual: QualityGateUI,
    tag: "MODULE.B",
  },
  {
    number: "COMP",
    title: "Intelligence Synthesis",
    description: "Complex papers and engineering blogs are distilled into strict, hyper-personalized briefs. We synthesize the signal; we don't just aggregate links.",
    visual: SynthesisUI,
    tag: "MODULE.C",
  },
  {
    number: "SYNC",
    title: "Cross-Platform Delivery",
    description: "Your technical context is pre-computed, compiled, and dispatched globally. Zero-latency access across all devices.",
    visual: GlobalFlowUI,
    tag: "MODULE.D",
  },
];

export default function HowItWorks() {
  return (
    <section
      id="process"
      className="relative w-full py-24 md:py-32 bg-paper text-ink font-sans border-b border-ink"
    >
      <div className="container mx-auto px-6 lg:px-12 max-w-7xl">
        {/* Section Head */}
        <div className="mb-20 grid grid-cols-1 md:grid-cols-2 gap-8 items-end border-b-4 border-ink pb-8">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 border-2 border-ink mb-6 bg-paper">
              <Layers size={14} className="text-ink" />
              <span className="text-xs font-mono font-bold tracking-widest uppercase text-ink">
                [/] Operational Pipeline
              </span>
            </div>
            <h2 className="text-5xl md:text-7xl font-bold font-display text-ink tracking-tighter uppercase leading-[0.9]">
              From Firehose <br />
              <span className="text-clay italic">
                To Signal.
              </span>
            </h2>
          </div>
          <div className="md:text-right font-mono text-sm max-w-md ml-auto leading-relaxed border-l-2 md:border-l-0 md:border-r-2 border-ink pl-4 md:pl-0 md:pr-4">
            The infrastructure mapping the noise into actionable architectural intelligence. Phase one establishes context; phase four distributes the compiled briefs.
          </div>
        </div>

        {/* 2x2 Numbered Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-ink border-2 border-ink">
          {steps.map((step, i) => (
            <div
              key={i}
              className="bg-paper flex flex-col group transition-all duration-300"
            >
              {/* Visual Area */}
              <div className="relative w-full h-[240px] border-b-2 border-ink bg-paper overflow-hidden">
                <step.visual />
                {/* Step Outline */}
                <div className="absolute inset-0 pointer-events-none border-[8px] border-paper z-20" />
              </div>

              {/* Text Content */}
              <div className="p-8 md:p-12 relative flex-1 flex flex-col justify-between hover-warm">
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <span className="text-xs font-mono text-ink font-bold tracking-widest border border-ink py-1 px-2">
                       [/] {step.tag}
                    </span>
                    <span className="text-sm font-mono font-bold tracking-tight text-clay border-b border-clay">
                       {step.number}
                    </span>
                  </div>
                  <h3 className="text-3xl font-display font-bold text-ink mb-4 tracking-tight uppercase group-hover:text-clay">
                    {step.title}
                  </h3>
                  <p className="text-ink font-mono text-sm leading-relaxed max-w-sm">
                    {step.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
