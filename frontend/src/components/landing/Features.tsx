import { motion } from "framer-motion";
import { Sparkles, Zap, Globe, Cpu, BarChart3, TrendingDown } from "lucide-react";

// Signal vs Noise Chart Component
const SignalChart = () => (
    <div className="relative w-full h-24 flex items-end gap-1 px-2">
        {[40, 70, 45, 90, 65, 80, 50, 95, 30, 85].map((h, i) => (
            <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ duration: 1, delay: i * 0.1, repeat: Infinity, repeatType: "reverse" }}
                className={`flex-1 rounded-t-sm ${i > 7 ? 'bg-[#B7397A]' : 'bg-white/10'}`}
            />
        ))}
        <div className="absolute top-0 right-4 text-[8px] font-mono text-[#B7397A] font-bold uppercase tracking-tighter">
            Pure Signal
        </div>
    </div>
);

const features = [
  {
    title: "The Firehose is Unmanageable",
    description: "Thousands of repositories, papers, and system design blogs drop every 24 hours. You can't read them all.",
    icon: Globe,
    className: "md:col-span-2",
    visual: () => (
        <div className="mt-6 flex flex-wrap gap-2 opacity-50 overflow-hidden h-12">
            {["ArXiv", "GitHub", "System Design", "vLLM", "KEDA", "PyTorch", "Kubernetes", "Next.js"].map((t, i) => (
                <span key={i} className="px-3 py-1 rounded-full border border-white/10 text-[9px] font-mono whitespace-nowrap">{t}</span>
            ))}
        </div>
    )
  },
  {
    title: "The Noise is Deafening",
    description: "Standard aggregators are flooded with SEO bait and marketing fluff that wastes your time.",
    icon: Zap,
    className: "md:col-span-1",
    visual: SignalChart
  },
  {
    title: "The Cost of Missing Out",
    description: "In AI and distributed systems, missing a paradigm shift means building obsolete tech.",
    icon: Cpu,
    className: "md:col-span-1",
    visual: () => (
        <div className="mt-6 p-4 rounded-xl bg-black/40 border border-white/5">
            <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] text-white/40 uppercase">Skill Relevance</span>
                <TrendingDown size={12} className="text-[#B7397A]" />
            </div>
            <div className="text-xl font-bold text-white leading-none">8.4 Months</div>
            <p className="text-[9px] text-white/30 mt-1 italic">Average time to architecture obsolescence</p>
        </div>
    )
  },
  {
    title: "Real-time Context Synthesis",
    description: "We don't just find links; we synthesize the global technical firehose into actionable intelligence.",
    icon: BarChart3,
    className: "md:col-span-2",
    visual: () => (
        <div className="mt-6 grid grid-cols-2 gap-4">
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div animate={{ x: [-100, 200] }} transition={{ duration: 3, repeat: Infinity }} className="h-full w-1/2 bg-gradient-to-r from-transparent via-[#B7397A] to-transparent" />
            </div>
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div animate={{ x: [-100, 200] }} transition={{ duration: 4, repeat: Infinity, delay: 0.5 }} className="h-full w-1/4 bg-gradient-to-r from-transparent via-[#4C6E94] to-transparent" />
            </div>
        </div>
    )
  }
];

export default function Features() {
  return (
    <section className="relative w-full py-48 bg-[#010101] overflow-hidden font-sans border-t border-white/5">
      {/* Background ambient glows */}
      <div className="absolute top-0 left-[-10%] w-[800px] h-[800px] bg-[#B7397A]/5 blur-[160px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-[-10%] w-[800px] h-[800px] bg-[#4C6E94]/5 blur-[160px] rounded-full pointer-events-none" />

      <div className="container mx-auto px-6 relative z-10 max-w-6xl">
        <div className="text-center mb-28 max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-6"
          >
            <Sparkles size={14} className="text-[#B7397A]" />
            <span className="text-xs font-semibold tracking-widest uppercase text-white/30">
               Engineering Challenges
            </span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-4xl md:text-5xl lg:text-7xl font-bold tracking-tighter text-white mb-8 leading-[0.9]"
          >
            The Tech Landscape Moves <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
              Too Fast for Manual Tracking.
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-lg text-white/50 max-w-2xl mx-auto leading-relaxed"
          >
            Managing technical context is a bandwidth problem. Standard search is 
            obsolete; you need an autonomous swarm to filter the flood.
          </motion.p>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 40, scale: 0.98 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: i * 0.1, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className={`group relative p-8 rounded-[2.5rem] bg-[rgba(28,27,36,0.3)] border border-white/10 hover:border-white/20 transition-all duration-500 overflow-hidden backdrop-blur-3xl flex flex-col justify-between ${feature.className}`}
            >
              <div className="relative z-10">
                <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-500">
                  <feature.icon size={20} className="text-white/70" />
                </div>
                <h3 className="text-xl font-bold text-white mb-4 tracking-tight">
                  {feature.title}
                </h3>
                <p className="text-white/50 text-sm leading-relaxed max-w-xs">
                  {feature.description}
                </p>
              </div>

              {/* Visual Element */}
              {feature.visual && <feature.visual />}

              {/* Hover Glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-[#B7397A]/0 to-[#4C6E94]/0 group-hover:from-[#B7397A]/5 group-hover:to-[#4C6E94]/5 transition-all duration-700 pointer-events-none" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
