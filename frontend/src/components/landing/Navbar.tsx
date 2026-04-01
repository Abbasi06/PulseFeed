import { motion, useScroll, useTransform } from "framer-motion";
import { useNavigate } from "react-router-dom";
import PulseFeedIcon from "../PulseFeedIcon";

export default function Navbar() {
  const navigate = useNavigate();
  const { scrollY } = useScroll();
  
  // Subtle bottom border appears as you scroll
  const borderOpacity = useTransform(scrollY, [0, 60], [0, 1]);

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 bg-paper"
      style={{
        borderBottom: "1px solid",
        borderColor: useTransform(borderOpacity, (v) => `rgba(35,31,32,${v * 0.15})`),
      }}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-10 flex items-center justify-between h-14">
        
        {/* Left: Logo */}
        <div
          className="flex items-center gap-2.5 cursor-pointer select-none"
          onClick={() => navigate("/")}
        >
          <PulseFeedIcon size={18} color="var(--color-ink)" />
          <span className="text-sm font-display font-bold tracking-tight text-ink uppercase">
            PulseFeed
          </span>
        </div>

        {/* Center: Navigation Links */}
        <div className="hidden md:flex items-center gap-8 text-[13px] font-sans font-medium text-ink/60">
          <a href="#process" className="hover:text-ink transition-colors duration-200">
            Product
          </a>
          <a href="#services" className="hover:text-ink transition-colors duration-200">
            Use Cases
          </a>
          <a href="#pricing" className="hover:text-ink transition-colors duration-200">
            Pricing
          </a>
          <a href="#work" className="hover:text-ink transition-colors duration-200">
            Architecture
          </a>
        </div>

        {/* Right: CTA */}
        <button
          onClick={() => navigate("/onboarding")}
          className="px-5 py-2 bg-clay text-paper text-[13px] font-display font-bold uppercase tracking-wider border-0 transition-none hover:bg-ink"
        >
          Start Your Swarm
        </button>
      </div>
    </motion.nav>
  );
}
