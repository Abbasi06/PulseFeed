import { motion, useScroll, useTransform } from "framer-motion";
import PulseFeedIcon from "../PulseFeedIcon";

const linkColumns = [
  {
    heading: "Product",
    links: ["Download", "Docs", "Changelog", "Releases"],
  },
  {
    heading: "Company",
    links: ["Manifesto", "Journal", "Press", "Comms"],
  },
  {
    heading: "Resources",
    links: ["Pricing", "Use Cases", "Data Policy", "Terms"],
  },
];

export default function Footer() {
  const { scrollYProgress } = useScroll();
  // Mega-text fades in and translates up as user reaches the bottom
  const megaOpacity = useTransform(scrollYProgress, [0.85, 1], [0, 1]);
  const megaY = useTransform(scrollYProgress, [0.85, 1], [60, 0]);

  return (
    <footer className="relative w-full bg-paper text-ink font-sans overflow-hidden z-10">
      {/* ── TOP LAYER: The Grid ── */}
      <div className="w-full max-w-[1400px] mx-auto px-6 lg:px-10 pt-24 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 md:gap-0">
          {/* Left: Tagline (spans 5 cols) */}
          <div className="md:col-span-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 mb-6">
                <PulseFeedIcon size={18} color="var(--color-ink)" />
                <span className="text-sm font-display font-bold tracking-tight text-ink uppercase">
                  PulseFeed
                </span>
              </div>
              <h3 className="text-3xl md:text-4xl font-display font-bold tracking-tight text-ink leading-[1.15] uppercase max-w-sm">
                Experience <br />
                <span className="text-clay italic">Pure Signal.</span>
              </h3>
            </div>
            <p className="mt-8 text-[11px] font-mono uppercase tracking-widest text-ink/40 font-bold">
              © {new Date().getFullYear()} PulseFeed.ai Inc.
            </p>
          </div>

          {/* Right: Link Columns (spans 7 cols) */}
          <div className="md:col-span-7 grid grid-cols-2 md:grid-cols-3 gap-10 md:pl-16">
            {linkColumns.map((col) => (
              <div key={col.heading} className="flex flex-col gap-3.5">
                <h5 className="text-[11px] font-mono font-bold tracking-widest uppercase text-ink/40 mb-1">
                  {col.heading}
                </h5>
                {col.links.map((link) => (
                  <a
                    key={link}
                    href="#"
                    className="text-[13px] font-sans font-medium text-ink hover:text-clay transition-colors duration-200"
                  >
                    {link}
                  </a>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Legal bottom row */}
        <div className="mt-16 pt-6 border-t border-ink/10 flex flex-col md:flex-row items-center justify-between gap-4 text-[11px] font-mono font-bold uppercase tracking-widest text-ink/30">
          <div className="flex gap-6">
            <a
              href="#"
              className="hover:text-ink transition-colors duration-200"
            >
              About
            </a>
            <a
              href="#"
              className="hover:text-ink transition-colors duration-200"
            >
              Privacy
            </a>
            <a
              href="#"
              className="hover:text-ink transition-colors duration-200"
            >
              Terms
            </a>
          </div>
          <div className="flex gap-6">
            <a
              href="#"
              className="hover:text-ink transition-colors duration-200"
            >
              X/Twitter
            </a>
            <a
              href="#"
              className="hover:text-ink transition-colors duration-200"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>

      {/* ── BOTTOM LAYER: Mega Typography ── */}
      <motion.div
        className="w-full overflow-hidden select-none pointer-events-none pb-0"
        style={{ opacity: megaOpacity, y: megaY }}
      >
        <h2
          className="text-ink font-display font-bold uppercase leading-[0.82] tracking-tighter whitespace-nowrap"
          style={{
            fontSize: "clamp(4rem, 15vw, 22rem)",
            marginBottom: "-0.08em",
          }}
        >
          PULSEFEED
        </h2>
      </motion.div>
    </footer>
  );
}
