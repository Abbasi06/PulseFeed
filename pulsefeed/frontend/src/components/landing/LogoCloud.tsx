import { motion } from "framer-motion";
import { InfiniteSlider } from "../ui/infinite-slider";

const SVG_LOGOS = [
  "https://html.tailus.io/blocks/customers/openai.svg",
  "https://html.tailus.io/blocks/customers/nvidia.svg",
  "https://html.tailus.io/blocks/customers/github.svg",
  "https://html.tailus.io/blocks/customers/tailwindcss.svg",
  "https://html.tailus.io/blocks/customers/vercel.svg",
];

const LOGO_NAMES = ["Stripe", "Vercel", "Linear", "Notion", "Figma"];

export default function LogoCloud() {
  return (
    <section className="relative w-full py-12 bg-[#010101] border-t border-b border-white/5 font-sans z-20">
      <div className="container mx-auto px-6 max-w-7xl">
        {/* "Trusted by" label */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
            <span className="text-xs font-semibold tracking-widest uppercase text-white/50">
              Trusted by the teams behind
            </span>
          </div>
        </motion.div>

        {/* Text logos (matching the reference style: clean text names) */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="hidden md:flex items-center justify-center gap-16 text-white/40"
        >
          {LOGO_NAMES.map((name) => (
            <span
              key={name}
              className="text-xl font-semibold tracking-tight hover:text-white/80 transition-colors duration-300 cursor-default"
            >
              {name}
            </span>
          ))}
        </motion.div>

        {/* Mobile: Infinite slider with SVG logos */}
        <div className="md:hidden w-full overflow-hidden">
          <InfiniteSlider gap={60} duration={25}>
            {SVG_LOGOS.map((src, i) => (
              <div
                key={i}
                className="flex items-center justify-center w-[100px] shrink-0 opacity-50 hover:opacity-100 transition-opacity duration-300"
              >
                <img
                  src={src}
                  alt="Partner Logo"
                  className="w-full h-auto brightness-0 invert object-contain max-h-[30px]"
                />
              </div>
            ))}
          </InfiniteSlider>
        </div>
      </div>
    </section>
  );
}
