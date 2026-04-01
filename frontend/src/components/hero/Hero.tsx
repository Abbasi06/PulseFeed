import { useNavigate } from "react-router-dom";
import { motion, Variants, useInView } from "framer-motion";
import { ArrowRight } from "lucide-react";
import PulseFeedIcon from "../PulseFeedIcon.jsx";
import { useRef } from "react";

const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: [0.21, 0.47, 0.32, 0.98] as const,
      delay: i * 0.15,
    },
  }),
};

const FloatingFragment = ({ children, className, delay = 0 }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.8, ease: "easeOut", delay }}
    className={`absolute p-4 print-panel border-ink border-2 pointer-events-none hidden lg:block ${className}`}
  >
    {children}
  </motion.div>
);

export default function Hero() {
  const navigate = useNavigate();
  const scrollRevealRef = useRef(null);
  const isInView = useInView(scrollRevealRef, { once: true, margin: "-80px" });

  return (
    <div className="relative w-full font-sans text-ink selection:bg-clay selection:text-paper border-b-2 border-ink">

      {/* ── SECTION 1: Terminal Masthead ── */}
      <div className="relative z-20 w-full min-h-[80vh] flex flex-col items-center justify-center border-b border-ink pt-20">
        
        <div className="flex items-center justify-between w-full max-w-6xl px-6 mb-12 font-mono text-xs uppercase tracking-widest border-b border-ink pb-4">
           <span>[/] Vol. 01 — The Knowledge Base</span>
           <span>Wednesday, April 1, 2026</span>
           <span>No Noise, Only Signal</span>
        </div>

        <motion.h1
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, ease: [0.21, 0.47, 0.32, 0.98] }}
          className="text-[80px] sm:text-[110px] md:text-[148px] font-bold leading-[0.9] tracking-tighter text-center select-none font-display uppercase"
        >
          Pulse <br/> Feed
        </motion.h1>

        {/* Scroll hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute bottom-0 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 pb-6"
        >
          <span className="text-ink font-mono text-[10px] tracking-[0.2em] uppercase">↓ Scroll</span>
          <div className="w-px h-12 bg-ink" />
        </motion.div>
      </div>

      {/* ── SECTION 2: Scroll-revealed Grid ── */}
      <div ref={scrollRevealRef} className="relative z-20 w-full grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-ink min-h-[60vh]">

        {/* Left Column (Meta data) */}
        <div className="lg:col-span-3 p-6 flex flex-col justify-between font-mono text-xs border-b lg:border-b-0 border-ink">
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-2 uppercase tracking-tighter border border-ink p-2 w-fit">
              <PulseFeedIcon size={12} color="var(--color-ink)" /> [/] Swarm_Log
            </div>
            <p className="leading-relaxed border-l-2 border-ink pl-3">
              [INFO] Ingesting ArXiv:2403.00123 <br />
              [OK] Vectorizing embeddings... <br />
              [EXEC] Synthesis initialized.
            </p>
            <div className="mt-8">
              <span className="font-bold underline decoration-clay underline-offset-4">[→] MATCH FOUND</span>
              <p className="mt-2 italic">Attention Is All You Need</p>
            </div>
          </div>
        </div>

        {/* Centre Column (Hero Copy & CTA) */}
        <div className="flex flex-col items-center text-center p-8 lg:p-16 lg:col-span-6 border-b lg:border-b-0 border-ink bg-paper relative">

          {/* Announcement pill */}
          <motion.div
            custom={0}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="flex items-center gap-3 px-3 py-1.5 mb-10 border-2 border-ink text-ink font-mono uppercase text-[10px] tracking-widest bg-paper"
          >
            <span className="text-clay font-bold">[⚡]</span>
            <span className="font-bold">
              Initialize your autonomous research swarm today
            </span>
          </motion.div>

          {/* Subtitle */}
          <motion.h2
            custom={1}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-2xl sm:text-3xl md:text-5xl font-display font-bold tracking-tight mb-8 max-w-3xl leading-[1.1] uppercase"
          >
            Autonomous Research Swarm for <br />
            <span className="italic text-clay">High-Signal Context.</span>
          </motion.h2>

          {/* Description */}
          <motion.p
            custom={2}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-base md:text-lg max-w-xl mb-12 leading-relaxed font-sans"
          >
            Ingest, Filter, and Synthesize the global firehose of ArXiv papers,
            GitHub repos, and engineering blogs into a hyper-personalized,
            zero-noise intelligence feed.
          </motion.p>

          {/* CTA */}
          <motion.div
            custom={3}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
          >
            <button
              onClick={() => navigate("/onboarding")}
              className="flex items-center gap-4 px-8 py-4 bg-clay text-paper font-display uppercase tracking-wider text-sm font-bold border-2 border-clay transition-none hover:bg-ink hover:border-ink hover:text-paper"
            >
              Start Your Swarm →
            </button>
          </motion.div>
        </div>

        {/* Right Column (Secondary Meta) */}
        <div className="lg:col-span-3 p-6 flex flex-col font-mono text-xs">
          <div className="p-4 border border-ink bg-paper">
            <div className="flex justify-between items-center mb-4 border-b border-ink pb-2">
              <span className="font-bold">[/] GITHUB_REPO</span>
              <span className="text-clay font-bold">vLLM</span>
            </div>
            <div className="space-y-4">
              <div className="h-2 w-full border border-ink overflow-hidden p-[1px]">
                <motion.div
                  animate={{ width: ["0%", "100%", "0%"] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  className="h-full bg-ink"
                />
              </div>
              <p className="italic">
                Aggregating 124 open PRs for synthesis phase...
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
