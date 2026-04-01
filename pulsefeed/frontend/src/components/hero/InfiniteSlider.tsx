import { motion } from "framer-motion";
import { Github } from "lucide-react";

const LOGOS = [
  {
    name: "OpenAI",
    icon: (
      <span className="font-sans font-bold text-xl tracking-tighter">
        OpenAI
      </span>
    ),
  },
  {
    name: "Nvidia",
    icon: <span className="font-sans font-black italic text-xl">NVIDIA</span>,
  },
  { name: "GitHub", icon: <Github size={28} /> },
];

export default function InfiniteSlider() {
  // Simple infinite scroll logo ticker
  return (
    <div className="w-full relative overflow-hidden h-24 mt-20 fade-edges">
      <div className="absolute inset-0 flex items-center w-[200%]">
        <motion.div
          className="flex flex-nowrap items-center w-1/2 justify-around"
          animate={{ x: ["0%", "-100%"] }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
        >
          {[...LOGOS, ...LOGOS, ...LOGOS].map((logo, idx) => (
            <div
              key={`${logo.name}-${idx}`}
              className="px-12 text-white/50 hover:text-white transition-colors duration-300 invert-0 flex items-center justify-center grayscale hover:grayscale-0"
            >
              {logo.icon}
            </div>
          ))}
        </motion.div>
        <motion.div
          className="flex flex-nowrap items-center w-1/2 justify-around"
          animate={{ x: ["0%", "-100%"] }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
        >
          {[...LOGOS, ...LOGOS, ...LOGOS].map((logo, idx) => (
            <div
              key={`dup-${logo.name}-${idx}`}
              className="px-12 text-white/50 hover:text-white transition-colors duration-300 invert-0 flex items-center justify-center grayscale hover:grayscale-0"
            >
              {logo.icon}
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
