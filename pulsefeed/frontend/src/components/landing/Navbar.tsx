import { motion, useScroll, useTransform } from "framer-motion";
import { useNavigate } from "react-router-dom";
import Logo from "../Logo";

// Maps each nav label to the section id it scrolls to
const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "Why Us", href: "#why-us" },
  { label: "How It Works", href: "#process" },
  { label: "Architecture", href: "#architecture" },
] as const;

export default function Navbar() {
  const navigate = useNavigate();
  const { scrollY } = useScroll();

  // Border fades in as user scrolls — keeps hero clean at the top
  const borderColor = useTransform(
    scrollY,
    [0, 60],
    ["rgba(35,31,32,0)", "rgba(35,31,32,0.15)"],
  );

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 bg-paper"
      style={{ borderBottom: "1px solid", borderColor }}
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-10 flex items-center justify-between h-14">
        {/* Left: logo + nav links grouped together */}
        <div className="flex items-center gap-8">
          <div
            className="cursor-pointer select-none shrink-0"
            onClick={() => navigate("/")}
          >
            <Logo size={30} variant="word" color="dark" />
          </div>

          <nav className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map(({ label, href }) => (
              <a
                key={href}
                href={href}
                className="text-[13px] font-sans font-medium text-ink/60 hover:text-ink transition-colors duration-200"
              >
                {label}
              </a>
            ))}
          </nav>
        </div>

        {/* Right: CTA */}
        <button
          onClick={() => navigate("/onboarding")}
          className="px-5 py-2 bg-clay text-paper text-[13px] font-display font-bold uppercase tracking-wider transition-all duration-300 hover:bg-ink shrink-0"
        >
          Start Pulsing
        </button>
      </div>
    </motion.nav>
  );
}
