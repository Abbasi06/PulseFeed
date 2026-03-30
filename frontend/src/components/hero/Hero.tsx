import { useNavigate } from "react-router-dom";
import {
  motion,
  Variants,
  useInView,
  useScroll,
  useTransform,
  useMotionTemplate,
} from "framer-motion";
import { ArrowRight, Zap } from "lucide-react";
import PulseFeedIcon from "../PulseFeedIcon.jsx";
import { useRef } from "react";
import HeroVideo from "./HeroVideo";
import ParticleField from "./ParticleField";

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
    initial={{ opacity: 0, scale: 0.9, y: 20 }}
    animate={{
      opacity: [0.4, 0.7, 0.4],
      scale: 1,
      y: [0, -10, 0],
      x: [0, 5, 0],
    }}
    transition={{
      duration: 5,
      repeat: Infinity,
      delay,
      opacity: { duration: 3, repeat: Infinity },
    }}
    className={`absolute p-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md shadow-2xl pointer-events-none hidden lg:block ${className}`}
  >
    {children}
  </motion.div>
);

export default function Hero() {
  const navigate = useNavigate();
  const scrollRevealRef = useRef(null);
  const isInView = useInView(scrollRevealRef, { once: true, margin: "-80px" });

  // Track raw document scroll — window.innerHeight ≈ 100vh
  const { scrollY } = useScroll();
  const vh = typeof window !== "undefined" ? window.innerHeight : 800;

  // Blur ramps in during the lower half of Section 1 and stays on for all subsequent sections
  const blurPx = useTransform(scrollY, [vh * 0.4, vh * 0.9], [0, 20]);
  const blurFilter = useMotionTemplate`blur(${blurPx}px)`;

  return (
    <div className="relative w-full font-sans selection:bg-[#B7397A]/30">

      {/* ── CSS particle background — compositor-threaded, zero JS loop ── */}
      <ParticleField />

      {/* ── Fixed blur overlay — scroll-driven ── */}
      <motion.div
        style={{ backdropFilter: blurFilter }}
        className="fixed inset-0 z-0 pointer-events-none"
      />

      {/* ── SECTION 1: Title only — sits above the overlay so it's always sharp ── */}
      <div className="relative z-20 w-full h-screen flex items-center justify-center">
        <motion.h1
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: [0.21, 0.47, 0.32, 0.98] }}
          className="text-[90px] sm:text-[124px] md:text-[164px] font-bold leading-[0.9] tracking-tighter text-center select-none"
        >
          <span className="text-white">Pulse</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">
            Feed
          </span>
        </motion.h1>

        {/* Scroll hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-white/30 text-xs tracking-widest uppercase">scroll</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            className="w-px h-8 bg-gradient-to-b from-white/30 to-transparent"
          />
        </motion.div>
      </div>

      {/* ── SECTION 2: Scroll-revealed subtitle + CTA ── */}
      <div ref={scrollRevealRef} className="relative z-20 w-full pt-24 pb-32">

        {/* Floating fragments — anchored to page edges, clear of centre content */}
        <FloatingFragment className="left-6 xl:left-14 top-20 w-64" delay={0.3}>
          <div className="flex items-center gap-2 mb-2 text-[10px] text-white/40 uppercase tracking-tighter">
            <PulseFeedIcon size={10} color="#B7397A" /> Swarm Log // 09:42:11
          </div>
          <p className="text-[11px] font-mono text-white/70 leading-tight">
            [INFO] Ingesting ArXiv:2403.00123 <br />
            [SUCCESS] Vectorizing embeddings... <br />
            [ACTION] Synthesis initialized.
          </p>
        </FloatingFragment>

        <FloatingFragment className="right-6 xl:right-14 top-12 w-56" delay={0.7}>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] font-bold text-white/60">GITHUB_REPO: vLLM</span>
          </div>
          <div className="space-y-1.5">
            <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
              <motion.div
                animate={{ x: [-100, 100] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="h-full w-1/3 bg-[#B7397A]"
              />
            </div>
            <p className="text-[10px] text-white/40 italic">
              Aggregating 124 open PRs for synthesis...
            </p>
          </div>
        </FloatingFragment>

        <FloatingFragment className="left-6 xl:left-14 top-64 w-60" delay={1.1}>
          <div className="px-2 py-1 rounded bg-[#B7397A]/20 border border-[#B7397A]/40 text-[9px] text-[#B7397A] font-bold w-fit mb-2">
            HIGH_SIGNAL MATCH
          </div>
          <h4 className="text-[12px] font-bold text-white mb-1">Attention Is All You Need</h4>
          <p className="text-[10px] text-white/50 leading-relaxed">
            The cornerstone of the Transformer architecture remains the core retrieval target...
          </p>
        </FloatingFragment>

        {/* Centre column */}
        <div className="flex flex-col items-center text-center px-4 max-w-4xl mx-auto w-full">

          {/* Announcement pill */}
          <motion.div
            custom={0}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="flex items-center gap-3 px-2 py-2 pr-6 mb-12 rounded-full bg-[rgba(28,27,36,0.3)] border border-white/10 backdrop-blur-md shadow-[0_0_30px_rgba(183,57,122,0.1)]"
          >
            <div className="flex items-center justify-center px-2.5 py-1.5 rounded-lg bg-gradient-to-br from-[#B7397A] to-[#4C6E94] shadow-[0_0_15px_rgba(183,57,122,0.6)]">
              <Zap size={13} className="text-white" />
            </div>
            <span className="text-sm font-medium text-gray-400 tracking-tight">
              Initialize your autonomous research swarm today.
            </span>
          </motion.div>

          {/* Subtitle */}
          <motion.p
            custom={1}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-xl sm:text-2xl md:text-3xl font-bold text-white/80 tracking-tight mb-8 max-w-3xl"
          >
            Autonomous Research Swarm for <br />
            <span className="text-[#B7397A] italic">High-Signal Technical Context.</span>
          </motion.p>

          {/* Description */}
          <motion.p
            custom={2}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-lg md:text-xl text-white/40 max-w-2xl mb-14 leading-relaxed font-medium"
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
            className="relative group"
          >
            <div className="absolute -inset-[3px] bg-gradient-to-r from-[#B7397A]/40 to-[#4C6E94]/40 rounded-full blur-sm opacity-50 group-hover:opacity-100 transition duration-500" />
            <div className="absolute -inset-[1px] bg-gradient-to-r from-[#B7397A]/60 to-[#4C6E94]/60 rounded-full" />
            <button
              onClick={() => navigate("/onboarding")}
              className="relative flex items-center gap-4 px-10 py-5 bg-white rounded-full text-black font-bold text-lg hover:scale-[1.02] transition-transform duration-300"
            >
              Start Your Swarm
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-tr from-[#B7397A] to-[#4C6E94]">
                <ArrowRight size={16} className="text-white shrink-0" />
              </div>
            </button>
          </motion.div>
        </div>
      </div>

      {/* Hero Video */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 2 }}
        className="relative z-20 w-full"
      >
        <HeroVideo
          src="https://customer-cbeadsgr09pnsezs.cloudflarestream.com/697945ca6b876878dba3b23fbd2f1561/manifest/video.m3u8"
          fallbackSrc="/_videos/v1/f0c78f536d5f21a047fb7792723a36f9d647daa1.mp4"
        />
      </motion.div>
    </div>
  );
}
