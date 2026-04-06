import Navbar from "../components/landing/Navbar";
import Hero from "../components/hero/Hero";
import Features from "../components/landing/Features";
import WhyUs from "../components/landing/WhyUs";
import HowItWorks from "../components/landing/HowItWorks";
import Architecture from "../components/landing/Architecture";
import CTA from "../components/landing/CTA";
import Footer from "../components/landing/Footer";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";

// ── Antigravity-style scroll-linked reveal wrapper ──
// Wraps each AIDA section with a smooth upward translate + fade
const revealVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1], // Antigravity frictionless easing
    },
  },
};

function ScrollReveal({ children, delay = 0 }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <motion.section
      ref={ref}
      variants={revealVariants}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{
        duration: 0.9,
        ease: [0.16, 1, 0.3, 1],
        delay,
      }}
      className="w-full flex flex-col"
    >
      {children}
    </motion.section>
  );
}

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen w-full overflow-x-hidden">
      {/* ── Header Region ── */}
      <header className="w-full shrink-0">
        <Navbar />
      </header>

      {/* ── Main Content Region ── */}
      <main className="flex-1 flex flex-col w-full">
        <section className="w-full flex flex-col">
          <Hero />
        </section>

        <ScrollReveal>
          <Features />
        </ScrollReveal>

        <ScrollReveal delay={0.05}>
          <WhyUs />
        </ScrollReveal>

        <ScrollReveal delay={0.05}>
          <HowItWorks />
        </ScrollReveal>

        <ScrollReveal delay={0.05}>
          <Architecture />
        </ScrollReveal>

        <ScrollReveal delay={0.05}>
          <CTA />
        </ScrollReveal>
      </main>

      {/* ── Footer Region ── */}
      <footer className="w-full shrink-0 mt-auto">
        <Footer />
      </footer>
    </div>
  );
}
