import {
  motion,
  useScroll,
  useTransform,
  AnimatePresence,
} from "framer-motion";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import Logo from "../Logo";

const NAV_LINKS = [
  { label: "Features", href: "#features" },
  { label: "Why Us", href: "#why-us" },
  { label: "How It Works", href: "#process" },
  { label: "Architecture", href: "#architecture" },
] as const;

export default function Navbar() {
  const navigate = useNavigate();
  const { scrollY } = useScroll();
  const [mobileOpen, setMobileOpen] = useState(false);

  const borderColor = useTransform(
    scrollY,
    [0, 60],
    ["rgba(35,31,32,0)", "rgba(35,31,32,0.15)"],
  );

  function handleNavClick(href: string) {
    setMobileOpen(false);
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <>
      <motion.nav
        className="fixed top-0 left-0 right-0 z-50 bg-paper"
        style={{ borderBottom: "1px solid", borderColor }}
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-10 flex items-center justify-between h-14">
          {/* Left: logo + desktop nav */}
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
                  onClick={(e) => {
                    e.preventDefault();
                    handleNavClick(href);
                  }}
                  className="text-[13px] font-sans font-medium text-ink/60 hover:text-ink transition-colors duration-200"
                >
                  {label}
                </a>
              ))}
            </nav>
          </div>

          {/* Right: CTA + hamburger */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/onboarding")}
              className="hidden md:block px-5 py-2 bg-clay text-paper text-[13px] font-display font-bold uppercase tracking-wider transition-all duration-300 hover:bg-ink shrink-0"
            >
              Start Pulsing
            </button>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen((o) => !o)}
              className="md:hidden flex flex-col gap-[5px] justify-center items-center w-8 h-8 shrink-0"
              aria-label="Toggle menu"
            >
              <motion.span
                animate={
                  mobileOpen ? { rotate: 45, y: 7 } : { rotate: 0, y: 0 }
                }
                transition={{ duration: 0.25 }}
                className="block w-5 h-[1.5px] bg-ink origin-center"
              />
              <motion.span
                animate={
                  mobileOpen
                    ? { opacity: 0, scaleX: 0 }
                    : { opacity: 1, scaleX: 1 }
                }
                transition={{ duration: 0.2 }}
                className="block w-5 h-[1.5px] bg-ink"
              />
              <motion.span
                animate={
                  mobileOpen ? { rotate: -45, y: -7 } : { rotate: 0, y: 0 }
                }
                transition={{ duration: 0.25 }}
                className="block w-5 h-[1.5px] bg-ink origin-center"
              />
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-ink/30 md:hidden"
              onClick={() => setMobileOpen(false)}
            />

            {/* Drawer panel */}
            <motion.div
              key="drawer"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="fixed top-14 left-0 right-0 z-50 bg-paper border-b-2 border-ink md:hidden"
            >
              <nav className="flex flex-col divide-y divide-ink/10">
                {NAV_LINKS.map(({ label, href }) => (
                  <a
                    key={href}
                    href={href}
                    onClick={(e) => {
                      e.preventDefault();
                      handleNavClick(href);
                    }}
                    className="px-6 py-4 text-sm font-mono font-bold uppercase tracking-widest text-ink hover:text-clay hover:bg-ink/5 transition-colors"
                  >
                    {label}
                  </a>
                ))}
                <div className="p-6">
                  <button
                    onClick={() => {
                      setMobileOpen(false);
                      navigate("/onboarding");
                    }}
                    className="w-full py-3 bg-clay text-paper font-display font-bold uppercase tracking-wider text-sm hover:bg-ink transition-none"
                  >
                    Start Pulsing →
                  </button>
                </div>
              </nav>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
