import { motion, useInView } from "framer-motion";
import { useRef, useEffect, useState } from "react";

interface StatItem {
  tag: string;
  value: number;
  suffix: string;
  label: string;
  sublabel: string;
}

const STATS: StatItem[] = [
  {
    tag: "[01]",
    value: 100,
    suffix: "+",
    label: "Daily Sources",
    sublabel: "ArXiv · GitHub · Blogs · Feeds",
  },
  {
    tag: "[02]",
    value: 85,
    suffix: "%",
    label: "Noise Eliminated",
    sublabel: "Pure signal. Zero SEO bait.",
  },
  {
    tag: "[03]",
    value: 6,
    suffix: "h",
    label: "Refresh Cycle",
    sublabel: "Always current intelligence",
  },
  {
    tag: "[04]",
    value: 10,
    suffix: "×",
    label: "Coverage Boost",
    sublabel: "vs. manual research",
  },
];

function CountUp({
  target,
  suffix,
  trigger,
}: {
  target: number;
  suffix: string;
  trigger: boolean;
}) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!trigger) return;
    let current = 0;
    const duration = 1600;
    const step = 16;
    const increment = target / (duration / step);

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, step);

    return () => clearInterval(timer);
  }, [trigger, target]);

  return (
    <>
      {count}
      {suffix}
    </>
  );
}

export default function Stats() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section
      ref={ref}
      className="relative z-10 w-full bg-ink text-paper font-sans border-b-4 border-ink"
    >
      <div
        className="grid grid-cols-2 lg:grid-cols-4 divide-paper/10"
        style={{ borderColor: "rgba(253,252,248,0.1)", display: "grid" }}
      >
        {STATS.map((stat, i) => (
          <motion.div
            key={stat.tag}
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{
              duration: 0.7,
              delay: i * 0.12,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="px-8 py-12 flex flex-col gap-3 relative overflow-hidden group cursor-default"
            style={{
              borderRight: i < 3 ? "1px solid rgba(253,252,248,0.1)" : "none",
              borderBottom: i < 2 ? "1px solid rgba(253,252,248,0.1)" : "none",
            }}
          >
            {/* Clay fill on hover */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "var(--color-clay)",
                opacity: 0,
                transition: "none",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLDivElement).style.opacity = "1")
              }
            />

            <div className="relative z-10 flex justify-between items-start">
              <span className="text-[10px] font-mono font-bold tracking-[0.2em] uppercase opacity-40">
                {stat.tag}
              </span>
              <motion.div
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, delay: i * 0.4 }}
                className="w-1.5 h-1.5 rounded-full bg-clay"
              />
            </div>

            <div className="relative z-10 text-5xl md:text-6xl xl:text-7xl font-display font-bold leading-none tracking-tighter tabular-nums">
              <CountUp
                target={stat.value}
                suffix={stat.suffix}
                trigger={isInView}
              />
            </div>

            <div className="relative z-10 border-t border-paper/10 pt-3">
              <div className="text-sm font-display font-bold uppercase tracking-tight">
                {stat.label}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-widest opacity-40 mt-1">
                {stat.sublabel}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
