import { useNavigate } from 'react-router-dom';
import { motion, Variants } from 'framer-motion';
import { Zap, ArrowRight } from 'lucide-react';
import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import HeroVideo from './HeroVideo';
import AntigravityField from './AntigravityField';
import { InfiniteSlider } from '../ui/infinite-slider';

const SVG_LOGOS = [
  "https://html.tailus.io/blocks/customers/openai.svg",
  "https://html.tailus.io/blocks/customers/nvidia.svg",
  "https://html.tailus.io/blocks/customers/github.svg",
  "https://html.tailus.io/blocks/customers/tailwindcss.svg",
  "https://html.tailus.io/blocks/customers/vercel.svg"
];

const staggerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 },
  },
};

const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.21, 0.47, 0.32, 0.98] as const } },
};

export default function Hero() {
  const navigate = useNavigate();

  return (
    <div className="relative w-full min-h-screen flex flex-col items-center justify-start bg-[#010101] overflow-hidden pt-32 font-sans selection:bg-[#B7397A]/30">

      {/* Particle Canvas Layer (z-0, behind everything) */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <Canvas
          camera={{ position: [0, 0, 20], fov: 60 }}
          gl={{ antialias: false, alpha: true }}
          style={{ background: 'transparent' }}
        >
          <ambientLight intensity={0.6} />
          <pointLight position={[10, 10, 10]} intensity={1.2} color="#B7397A" />
          <pointLight position={[-10, -10, 5]} intensity={0.8} color="#D1E8E2" />
          <Suspense fallback={null}>
            <AntigravityField />
          </Suspense>
        </Canvas>
      </div>

      {/* Background radial glow */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-gradient-to-r from-[#B7397A]/20 via-[#4C6E94]/20 to-[#D1E8E2]/10 blur-[100px] rounded-full pointer-events-none z-0" />

      {/* Hero Content Layer (z-20) */}
      <motion.div
        variants={staggerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-20 flex flex-col items-center text-center px-4 max-w-5xl mx-auto w-full"
      >

        {/* Announcement Pill */}
        <motion.div
           variants={fadeUpVariants}
           className="flex items-center gap-3 px-2 py-2 pr-6 mb-10 rounded-full bg-[rgba(28,27,36,0.15)] border border-white/10 backdrop-blur-md shadow-[0_0_20px_rgba(183,57,122,0.08)]"
        >
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-[#B7397A] to-[#4C6E94] shadow-[0_0_15px_rgba(183,57,122,0.6)]">
            <Zap size={16} className="text-white fill-white" />
          </div>
          <span className="text-sm font-medium text-gray-300">Your personalized AI knowledge feed — updated daily.</span>
        </motion.div>

        {/* App title */}
        <motion.h1
           variants={fadeUpVariants}
           className="text-[56px] sm:text-[72px] md:text-[90px] font-bold leading-[1.0] tracking-tight mb-4"
        >
          <span className="text-white">Pulse</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94]">Feed</span>
        </motion.h1>

        {/* Subtitle — "Stay ahead of your field" */}
        <motion.p
           variants={fadeUpVariants}
           className="text-xl sm:text-2xl md:text-3xl font-medium text-white/55 tracking-tight mb-8"
        >
          Stay ahead of your field.
        </motion.p>

        {/* Subheadline */}
        <motion.p
           variants={fadeUpVariants}
           className="text-lg md:text-xl text-white/70 max-w-2xl mb-12 leading-relaxed"
        >
          PulseFeed curates the latest research, articles, and events tailored to your role — so you spend less time searching and more time building.
        </motion.p>

        {/* CTA Button */}
        <motion.div variants={fadeUpVariants} className="relative group">
          <div className="absolute -inset-[3px] bg-gradient-to-r from-[#B7397A]/40 to-[#4C6E94]/40 rounded-full blur-sm opacity-50 group-hover:opacity-100 transition duration-500" />
          <div className="absolute -inset-[1px] bg-gradient-to-r from-[#B7397A]/60 to-[#4C6E94]/60 rounded-full" />

          <button
            onClick={() => navigate('/onboarding')}
            className="relative flex items-center gap-4 px-8 py-4 bg-white rounded-full text-black font-semibold text-lg hover:scale-[1.02] transition-transform duration-300"
          >
            Start Your Feed
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-tr from-[#B7397A] to-[#4C6E94]">
               <ArrowRight size={16} className="text-white shrink-0" />
            </div>
          </button>
        </motion.div>

      </motion.div>

      {/* Hero Video (z-10, overlapping behind text using negative margin) */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8, duration: 2 }}
        className="w-full z-10"
      >
        <HeroVideo
           src="https://customer-cbeadsgr09pnsezs.cloudflarestream.com/697945ca6b876878dba3b23fbd2f1561/manifest/video.m3u8"
           fallbackSrc="/_videos/v1/f0c78f536d5f21a047fb7792723a36f9d647daa1.mp4"
        />
      </motion.div>

      {/* Logo Cloud Section */}
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 1, duration: 1 }}
        className="relative z-30 w-full mt-[-60px] md:mt-[-100px]"
      >
        <div className="w-full bg-black/20 backdrop-blur-sm border-t border-white/5 pb-8 pt-6 sm:py-8">
            <div className="max-w-7xl mx-auto px-6 h-full flex flex-col md:flex-row items-center justify-between gap-8 md:gap-12">

               <div className="flex-shrink-0 text-center md:text-left">
                  <p className="text-sm font-medium text-white/60 tracking-wide uppercase">Powered by</p>
               </div>

               <div className="hidden md:block w-[1px] h-12 bg-white/10" />

               <div className="w-full max-w-[800px] overflow-hidden">
                  <InfiniteSlider gap={60} duration={30}>
                     {SVG_LOGOS.map((src, i) => (
                        <div key={i} className="flex items-center justify-center w-[120px] shrink-0 opacity-50 hover:opacity-100 transition-opacity duration-300">
                           <img
                              src={src}
                              alt="Partner Logo"
                              className="w-full h-auto brightness-0 invert object-contain max-h-[40px]"
                           />
                        </div>
                     ))}
                  </InfiniteSlider>
               </div>

            </div>
        </div>
      </motion.div>

    </div>
  );
}
