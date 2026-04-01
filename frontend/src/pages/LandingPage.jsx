import Hero from "../components/hero/Hero";
import Features from "../components/landing/Features";
import WhyUs from "../components/landing/WhyUs";
import HowItWorks from "../components/landing/HowItWorks";
import Architecture from "../components/landing/Architecture";
import CTA from "../components/landing/CTA";
import Footer from "../components/landing/Footer";

export default function LandingPage() {
  return (
    <main className="bg-transparent min-h-screen w-full font-sans text-ink overflow-x-hidden">
      <Hero />
      <Features />
      <WhyUs />
      <HowItWorks />
      <Architecture />
      <CTA />
      <Footer />
    </main>
  );
}
