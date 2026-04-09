import Navbar from "../components/landing/Navbar";
import Hero from "../components/hero/Hero";
import Stats from "../components/landing/Stats";
import Ticker from "../components/landing/Ticker";
import Features from "../components/landing/Features";
import WhyUs from "../components/landing/WhyUs";
import HowItWorks from "../components/landing/HowItWorks";
import Architecture from "../components/landing/Architecture";
import Testimonials from "../components/landing/Testimonials";
import CTA from "../components/landing/CTA";
import Footer from "../components/landing/Footer";
import { motion, useInView } from "framer-motion";
import { useRef } from "react";

// ── Antigravity-style scroll-linked reveal wrapper ──
const revealVariants = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.9,
      ease: [0.16, 1, 0.3, 1],
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
      {/* ── Header ── */}
      <header className="w-full shrink-0">
        <Navbar />
      </header>

      {/* ── Main Content ── */}
      <main className="flex-1 flex flex-col w-full">
        {/* Hero — full viewport radar + below-fold reveal */}
        <section className="w-full flex flex-col">
          <Hero />
        </section>

        {/* Stats bar — dark, count-up numbers */}
        <Stats />

        {/* Ticker — dual infinite marquee of live data sources */}
        <Ticker />

        {/* Features — 2×2 problem/solution grid */}
        <ScrollReveal>
          <Features />
        </ScrollReveal>

        {/* Why Us — orbiting diagram + terminal */}
        <ScrollReveal delay={0.05}>
          <WhyUs />
        </ScrollReveal>

        {/* How It Works — 4-step pipeline */}
        <ScrollReveal delay={0.05}>
          <HowItWorks />
        </ScrollReveal>

        {/* Architecture — radial node diagram */}
        <ScrollReveal delay={0.05}>
          <Architecture />
        </ScrollReveal>

        {/* Testimonials — brutalist 3×2 field reports */}
        <ScrollReveal delay={0.05}>
          <Testimonials />
        </ScrollReveal>

        {/* CTA — dark section with live feed preview */}
        <ScrollReveal delay={0.05}>
          <CTA />
        </ScrollReveal>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full shrink-0 mt-auto">
        <Footer />
      </footer>
    </div>
  );
}
