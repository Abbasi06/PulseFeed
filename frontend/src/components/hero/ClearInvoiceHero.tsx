import { Canvas } from "@react-three/fiber";
import { motion, Variants, useInView } from "framer-motion";
import { useRef } from "react";
import BackgroundVideo from "./BackgroundVideo";
import AntigravityField from "./AntigravityField";
import InfiniteSlider from "./InfiniteSlider";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.2, delayChildren: 0.3 },
  },
};

const childVariants: Variants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } },
};

export default function ClearInvoiceHero() {
  const containerRef = useRef(null);
  const isInView = useInView(containerRef);

  return (
    <div ref={containerRef} className="relative w-full min-h-screen bg-true-black text-off-white overflow-hidden font-sans">
      {/* 5px Gradient Top Bar */}
      <div className="absolute top-0 left-0 w-full h-[5px] bg-gradient-to-r from-steel-blue via-aurora-pink to-mint-glow z-50" />

      {/* 3D Particle Engine Canvas */}
      <div className="absolute inset-0 z-[-20]">
        <Canvas frameloop={isInView ? "always" : "never"} camera={{ position: [0, 0, 15], fov: 45 }} dpr={[1, 2]}>
          <ambientLight intensity={0.5} />
          <AntigravityField inView={isInView} />
        </Canvas>
      </div>

      {/* HLS Background Video */}
      <BackgroundVideo src="https://stream.mux.com/hUT6X11m1Vkw1QMxPOLgI761x2cfpi9bHFbi5cNg4014.m3u8" />

      {/* Liquid Glass Navbar */}
      <nav className="relative z-40 flex items-center justify-between px-8 py-5 mt-1 liquid-glass mx-4 sm:mx-8 md:mx-16 rounded-2xl md:mx-auto max-w-7xl top-6">
        <div className="font-bold text-xl tracking-wide flex items-center gap-2">
          <span className="w-8 h-8 rounded-full bg-gradient-to-br from-mint-glow to-aurora-pink"></span>
          PulseBoard
        </div>
        <div className="hidden md:flex gap-8 text-sm font-medium text-off-white/80">
          <a href="#features" className="hover:text-white transition-colors">
            Features
          </a>
          <a href="#engine" className="hover:text-white transition-colors">
            Antigravity Engine
          </a>
          <a href="#pricing" className="hover:text-white transition-colors">
            Pricing
          </a>
        </div>
        <button className="px-5 py-2 text-sm font-bold bg-white text-true-black rounded-full hover:bg-mint-glow transition-colors">
          Get Access
        </button>
      </nav>

      {/* Hero Content */}
      <div className="relative z-30 flex flex-col items-center justify-center pt-40 px-4 text-center">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center max-w-4xl"
        >
          <motion.div
            variants={childVariants}
            className="mb-6 px-4 py-1.5 rounded-full liquid-glass text-sm font-medium text-mint-glow border border-mint-glow/30 flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-mint-glow animate-pulse"></span>
            Zero-Gravity Data Lab
          </motion.div>

          <motion.h1
            variants={childVariants}
            className="font-switzer text-6xl md:text-[5.5rem] font-black tracking-tighter leading-[1.05] mb-8"
          >
            Evolve Your <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-aurora-pink">
              Information Intake.
            </span>
          </motion.h1>

          <motion.p
            variants={childVariants}
            className="text-lg md:text-xl text-off-white/70 max-w-2xl mb-12 font-light"
          >
            Experience the next generation of SaaS data synthesis. Frictionless
            processing meets stunning visual intelligence.
          </motion.p>

          <motion.div
            variants={childVariants}
            className="flex flex-col sm:flex-row items-center gap-6"
          >
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-aurora-pink to-steel-blue rounded-full blur-lg opacity-70 group-hover:opacity-100 transition duration-500"></div>
              <button className="relative px-8 py-4 bg-gradient-to-r from-aurora-pink to-steel-blue rounded-full text-white font-bold text-lg hover:scale-105 transition-transform duration-300">
                Start Your Engine
              </button>
            </div>
            <button className="px-8 py-4 rounded-full liquid-glass text-white font-bold text-lg hover:bg-white/10 transition-colors duration-300">
              View Documentation
            </button>
          </motion.div>
        </motion.div>
      </div>

      {/* Infinite Logo Slider */}
      <div
        className="relative z-30 mt-[10vh] max-w-6xl mx-auto opacity-70"
        style={{
          WebkitMaskImage:
            "linear-gradient(to right, transparent, black 15%, black 85%, transparent)",
        }}
      >
        <p className="text-center text-sm text-off-white/50 mb-4 font-mono uppercase tracking-widest hidden md:block">
          Trusted by frontier teams
        </p>
        <InfiniteSlider />
      </div>
    </div>
  );
}
