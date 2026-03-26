import { motion, useScroll, useTransform } from "framer-motion";
import { useNavigate } from "react-router-dom";
import PulseFeedIcon from "../PulseFeedIcon";
import { ArrowUpRight } from "lucide-react";

export default function Navbar() {
  const navigate = useNavigate();
  const { scrollY } = useScroll();
  const bgOpacity = useTransform(scrollY, [0, 100], [0.1, 0.4]);
  const blurValue = useTransform(scrollY, [0, 100], [4, 16]);

  return (
    <motion.nav
      className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center justify-between w-[90%] max-w-4xl px-4 py-2 rounded-full border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.5)]"
      style={{
        backgroundColor: bgOpacity,
        backdropFilter: blurValue,
        WebkitBackdropFilter: "blur(16px)",
      }}
      initial={{ y: -50, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <div
        className="flex items-center gap-2 px-2 cursor-pointer"
        onClick={() => navigate("/")}
      >
        <div className="w-6 h-6 flex items-center justify-center rounded-md bg-gradient-to-br from-[#B7397A] to-[#4C6E94] shadow-[0_0_10px_rgba(183,57,122,0.4)]">
          <PulseFeedIcon size={12} color="white" />
        </div>
        <span className="text-white font-semibold tracking-tight">
          PulseFeed.ai
        </span>
      </div>

      <div className="hidden md:flex items-center gap-6 text-sm font-medium text-white/50">
        <a href="#home" className="hover:text-white transition-colors">
          Home
        </a>
        <a href="#services" className="hover:text-white transition-colors">
          Services
        </a>
        <a href="#work" className="hover:text-white transition-colors">
          Work
        </a>
        <a href="#process" className="hover:text-white transition-colors">
          Process
        </a>
        <a href="#pricing" className="hover:text-white transition-colors">
          Pricing
        </a>
      </div>

      <button
        onClick={() => navigate("/onboarding")}
        className="flex items-center gap-2 bg-white text-black px-4 py-1.5 rounded-full text-sm font-semibold hover:bg-gray-200 transition-colors"
      >
        Get Started <ArrowUpRight size={14} />
      </button>
    </motion.nav>
  );
}
