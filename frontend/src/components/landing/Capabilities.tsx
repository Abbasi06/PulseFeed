import { motion } from "framer-motion";

export default function Capabilities() {
  const blocks = [
    {
      id: 1,
      title: "The Agentic Sourcing Swarm",
      description:
        "Tell us your role (e.g., Gen AI Engineer) and your sub-fields (e.g., Agentic Workflows, vLLM, KEDA). Our background workers parallelize 10+ concurrent research missions across the internet's highest-signal domains, hunting for breakthroughs while you sleep.",
      gradient: "from-[#B7397A]/20 to-transparent",
      visual: (
        <div className="relative w-48 h-32 rounded-xl border border-white/10 bg-[rgba(255,255,255,0.05)] shadow-2xl backdrop-blur-md flex flex-col p-4">
          <div className="flex gap-1.5 mb-4">
            <div className="w-2.5 h-2.5 rounded-full bg-[#B7397A] animate-pulse" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#B7397A] animate-pulse delay-75" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#B7397A] animate-pulse delay-150" />
          </div>
          <div className="h-2 w-3/4 rounded bg-white/20 mb-2" />
          <div className="h-2 w-1/2 rounded bg-white/10 mb-4" />
          <div className="mt-auto h-8 w-18 self-end rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
            <span className="text-[8px] text-white/50 uppercase tracking-widest font-bold">Scanning...</span>
          </div>
        </div>
      ),
    },
    {
      id: 2,
      title: "The 85% Noise Reduction Guarantee",
      description:
        "We don't do basic keyword matching. Every piece of ingested data passes through a strict LLM-based Quality Gate. If an article lacks technical density or reads like a marketing brochure, it is permanently dropped. You only see the elite 15%.",
      gradient: "from-[#7c3aed]/20 to-transparent",
      visual: (
        <div className="relative w-48 h-32 rounded-xl border border-white/10 bg-[rgba(255,255,255,0.05)] shadow-2xl backdrop-blur-md flex flex-col items-center justify-center p-4">
          <div className="text-3xl font-bold text-white mb-2">15%</div>
          <div className="text-[10px] text-white/50 uppercase tracking-widest font-bold">High Signal Density</div>
        </div>
      ),
    },
    {
      id: 3,
      title: "The 10X Synthesis Engine",
      description:
        "No more reading 40-page PDFs just to find out if the methodology is relevant. PulseFeed distills complex architectures into a 3-sentence technical summary, exact framework keywords, and immediate source links.",
      gradient: "from-[#4C6E94]/20 to-transparent",
      visual: (
        <div className="relative w-48 h-32 rounded-xl border border-white/10 bg-[rgba(255,255,255,0.05)] shadow-2xl backdrop-blur-md flex flex-col p-4">
          <div className="h-1.5 w-full rounded bg-white/30 mb-2" />
          <div className="h-1.5 w-full rounded bg-white/20 mb-2" />
          <div className="h-1.5 w-full rounded bg-white/10 mb-2" />
          <div className="divider h-px w-full bg-white/10 my-2" />
          <div className="h-1.5 w-3/4 rounded bg-[#7c3aed]/40 mb-1" />
          <div className="h-1.5 w-2/3 rounded bg-[#7c3aed]/30" />
        </div>
      ),
    },
  ];

  return (
    <section className="relative w-full py-24 bg-[#010101] font-sans">
      <div className="container mx-auto px-6 max-w-5xl">
        <div className="text-center mb-16 px-4">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm mb-6"
          >
            <span className="text-xs font-semibold tracking-widest uppercase text-white/50">
              The Solution
            </span>
          </motion.div>

          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-6 leading-tight"
          >
            Stop Searching. <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
              Start Absorbing.
            </span>
          </motion.h2>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ delay: 0.2 }}
            className="text-lg text-white/50 max-w-2xl mx-auto"
          >
            PulseFeed isn’t a news reader. It’s a distributed inference engine working exclusively for your career.
          </motion.p>
        </div>

        <div className="space-y-6">
          {blocks.map((block, idx) => (
            <motion.div
              key={block.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.7 }}
              className={`relative w-full rounded-[2rem] border border-white/10 bg-[rgba(28,27,36,0.2)] backdrop-blur-xl overflow-hidden flex flex-col ${
                idx % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } shadow-[0_8px_40px_rgba(0,0,0,0.5)]`}
            >
              <div className="flex-1 p-10 md:p-14 flex flex-col justify-center">
                <h3 className="text-2xl md:text-3xl font-bold text-white mb-4 leading-tight">
                  {block.title}
                </h3>
                <p className="text-white/50 text-base leading-relaxed">
                  {block.description}
                </p>
              </div>
              <div className="flex-1 min-h-[250px] md:min-h-[auto] relative bg-[#010101]/50 flex items-center justify-center p-12">
                <div className={`absolute inset-0 bg-gradient-to-${idx % 2 === 0 ? "l" : "r"} ${block.gradient} pointer-events-none`} />
                {block.visual}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
