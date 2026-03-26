import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Play } from "lucide-react";
import PulseFeedIcon from "../PulseFeedIcon";
import HeroVideo from "../hero/HeroVideo";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: 0.15 * i,
      duration: 0.8,
      ease: [0.21, 0.47, 0.32, 0.98],
    },
  }),
};

export default function HeroSection() {
  const navigate = useNavigate();

  return (
    <section
      id="home"
      className="relative w-full min-h-screen flex flex-col items-center justify-start bg-[#010101] overflow-hidden pt-36 pb-0 font-sans selection:bg-[#B7397A]/30"
    >
      {/* Background radial glows */}
      <div className="absolute top-[-15%] left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-gradient-to-r from-[#B7397A]/15 via-[#7c3aed]/10 to-[#4C6E94]/10 blur-[120px] rounded-full pointer-events-none z-0" />

      {/* Content */}
      <div className="relative z-20 flex flex-col items-center text-center px-6 max-w-5xl mx-auto w-full">
        {/* Announcement Pill */}
        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="flex items-center gap-3 px-2 py-2 pr-6 mb-10 rounded-full bg-[rgba(28,27,36,0.15)] border border-white/10 backdrop-blur-md shadow-[0_0_20px_rgba(183,57,122,0.08)]"
        >
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10">
            <span className="text-[11px] font-bold tracking-wider uppercase text-white/80">
              New
            </span>
          </div>
          <span className="text-sm font-medium text-gray-300">
            Introducing AI-powered knowledge curation.
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          custom={1}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="text-[42px] sm:text-[60px] md:text-[76px] lg:text-[88px] font-bold leading-[1.05] tracking-tight mb-6"
        >
          <span className="text-white">Outpace the Industry.</span>
          <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94] italic px-2">
            10X
          </span>
          <span className="text-white">Your Technical Context.</span>
        </motion.h1>

        <motion.p
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="text-lg md:text-xl text-white/70 max-w-4xl mb-12 leading-relaxed"
        >
          PulseFeed is an autonomous, multi-agent research swarm. We ingest,
          filter, and synthesize the global firehose of ArXiv papers, GitHub
          repos, and engineering blogs into a hyper-personalized, zero-noise
          intelligence feed.
        </motion.p>

        {/* Buttons Row */}
        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          {/* Primary Button */}
          <div className="relative group">
            <div className="absolute -inset-[3px] bg-gradient-to-r from-[#B7397A]/40 to-[#4C6E94]/40 rounded-full blur-sm opacity-50 group-hover:opacity-100 transition duration-500" />
            <div className="absolute -inset-[1px] bg-gradient-to-r from-[#B7397A]/60 to-[#4C6E94]/60 rounded-full" />
            <button
              onClick={() => navigate("/onboarding")}
              className="relative flex items-center gap-3 px-8 py-4 bg-white rounded-full text-black font-semibold text-base hover:scale-[1.02] transition-transform duration-300"
            >
              Initialize Your Swarm
              <ArrowRight size={16} className="shrink-0" />
            </button>
          </div>

          {/* Secondary Button */}
          <button className="flex items-center gap-3 px-8 py-4 rounded-full border border-white/15 bg-white/5 text-white/80 font-medium text-base hover:bg-white/10 transition-colors duration-300 backdrop-blur-sm">
            <Play size={14} className="shrink-0 fill-white/80" />
            See How It Works
          </button>
        </motion.div>
      </div>

      {/* Hero Video — slotted below the CTA, overlapping with negative margin */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 2 }}
        className="w-full z-10 mt-12"
      >
        <HeroVideo
          src="https://customer-cbeadsgr09pnsezs.cloudflarestream.com/697945ca6b876878dba3b23fbd2f1561/manifest/video.m3u8"
          fallbackSrc="/_videos/v1/f0c78f536d5f21a047fb7792723a36f9d647daa1.mp4"
        />
      </motion.div>
    </section>
  );
}
