import { useNavigate } from "react-router-dom";
import { motion, Variants, useInView } from "framer-motion";
import PulseFeedIcon from "../PulseFeedIcon.jsx";
import { useRef } from "react";

const CX = 450;
const CY = 310;

const RINGS = Array.from({ length: 28 }, (_, i) => {
  const t = i / 27;
  return {
    r: 175 + t * 370, // 175 → 545
    baseWidth: i % 4 === 0 ? 1.2 : 0.55,
    baseOpacity: 0.75 - t * 0.65, // 0.75 → 0.10
    gapLen: (6 + t * 18).toFixed(1), // 6 → 24
    rotateDur: 300 + i * 20,
    reverse: i % 2 === 0,
  };
});

const GOLDEN_ANGLE = 2.39996323;
const DOTS = Array.from({ length: 55 }, (_, i) => {
  const angle = i * GOLDEN_ANGLE;
  const radius = 200 + i * 3.2;
  const bx = Math.cos(angle) > 0 ? 1.1 : 0.75;
  return {
    x: CX + Math.cos(angle) * radius * bx,
    y: CY + Math.sin(angle) * radius * 0.88,
    r: 0.6 + (i % 5) * 0.35,
    o: 0.1 + (i % 6) * 0.055,
  };
});

const WAVE_PERIOD = 6;
const RING_STAGGER = 0.09;
const PULSE_DUR = 0.9;

function buildRingCSS(): string {
  const base = `
    @keyframes rcw  { to { transform: rotate( 360deg); } }
    @keyframes rccw { to { transform: rotate(-360deg); } }
  `;

  const perRing = RINGS.map((ring, i) => {
    const peakW = (ring.baseWidth * 2.5).toFixed(2);
    const peakO = Math.min(ring.baseOpacity + 0.72, 0.95).toFixed(2);
    const peakPct = (((PULSE_DUR * 0.15) / WAVE_PERIOD) * 100).toFixed(2);
    const endPct = ((PULSE_DUR / WAVE_PERIOD) * 100).toFixed(2);

    return (
      `@keyframes rp${i}{` +
      `0%{stroke:#26498D;stroke-width:${ring.baseWidth};opacity:${ring.baseOpacity};animation-timing-function:ease-out}` +
      `${peakPct}%{stroke:#26498D;stroke-width:${peakW};opacity:${peakO};animation-timing-function:ease-out}` +
      `${endPct}%,100%{stroke:#26498D;stroke-width:${ring.baseWidth};opacity:${ring.baseOpacity}}` +
      `}`
    );
  });

  return base + perRing.join("\n");
}

const RING_CSS = buildRingCSS();

const fadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: [0.21, 0.47, 0.32, 0.98] as const,
      delay: i * 0.15,
    },
  }),
};

function RadarField() {
  return (
    <svg
      viewBox="0 0 900 620"
      preserveAspectRatio="xMidYMid meet"
      className="absolute inset-0 w-full h-full"
      aria-hidden="true"
    >
      <defs>
        <style>{RING_CSS}</style>
      </defs>

      {DOTS.map((d, i) => (
        <circle
          key={`dot-${i}`}
          cx={d.x}
          cy={d.y}
          r={d.r}
          fill="var(--color-nautical)"
          opacity={d.o}
        />
      ))}

      {RINGS.map((ring, i) => {
        const delay = (i * RING_STAGGER).toFixed(3);

        return (
          <g
            key={`ring-${i}`}
            style={
              {
                transformBox: "fill-box",
                transformOrigin: "center",
                animation: `${ring.reverse ? "rccw" : "rcw"} ${ring.rotateDur}s linear infinite`,
              } as React.CSSProperties
            }
          >
            <circle
              cx={CX}
              cy={CY}
              r={ring.r}
              fill="none"
              stroke="#26498D"
              strokeWidth={ring.baseWidth}
              strokeLinecap="round"
              strokeDasharray={`0.5 ${ring.gapLen}`}
              opacity={ring.baseOpacity}
              style={{
                animation: `rp${i} ${WAVE_PERIOD}s ${delay}s linear infinite`,
              }}
            />
          </g>
        );
      })}
    </svg>
  );
}

export default function Hero() {
  const navigate = useNavigate();
  const scrollRevealRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(scrollRevealRef, { once: true, margin: "-80px" });

  return (
    <div className="relative w-full font-sans text-ink selection:bg-clay selection:text-paper border-b-2 border-ink">
      <div className="relative z-20 w-full min-h-screen flex items-center justify-center border-b border-ink overflow-hidden">
        <RadarField />

        <motion.h1
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.3, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-10 text-[clamp(4rem,12vw,10rem)] font-bold leading-[0.85] tracking-tighter text-center select-none font-display uppercase"
        >
          Pulse <br /> Feed
        </motion.h1>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4, duration: 0.8 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
        >
          <span className="text-ink font-mono text-[10px] tracking-[0.25em] uppercase">
            ↓ Scroll
          </span>
          <motion.div
            animate={{ scaleY: [1, 0.35, 1] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
            className="w-px h-10 bg-ink origin-top"
          />
        </motion.div>
      </div>

      <div
        ref={scrollRevealRef}
        className="relative z-20 w-full grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-ink min-h-[60vh]"
      >
        <div className="lg:col-span-3 p-6 flex flex-col justify-between font-mono text-xs border-b lg:border-b-0 border-ink">
          <div className="space-y-6">
            <div className="flex items-center gap-2 mb-2 uppercase tracking-tighter border border-ink p-2 w-fit">
              <PulseFeedIcon size={12} color="var(--color-ink)" /> [/] Swarm_Log
            </div>
            <p className="leading-relaxed border-l-2 border-ink pl-3">
              [INFO] Ingesting ArXiv:2403.00123 <br />
              [OK] Vectorizing embeddings... <br />
              [EXEC] Synthesis initialized.
            </p>
            <div className="mt-8">
              <span className="font-bold underline decoration-clay underline-offset-4">
                [→] MATCH FOUND
              </span>
              <p className="mt-2 italic">Attention Is All You Need</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col items-center text-center p-8 lg:p-16 lg:col-span-6 border-b lg:border-b-0 border-ink bg-paper relative">
          <motion.div
            custom={0}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="flex items-center gap-3 px-3 py-1.5 mb-10 border-2 border-ink text-ink font-mono uppercase text-[10px] tracking-widest bg-paper"
          >
            <span className="text-clay font-bold">[⚡]</span>
            <span className="font-bold">
              Initialize your autonomous research swarm today
            </span>
          </motion.div>

          <motion.h2
            custom={1}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-2xl sm:text-3xl md:text-5xl font-display font-bold tracking-tight mb-8 max-w-3xl leading-[1.1] uppercase"
          >
            Autonomous Research Swarm for <br />
            <span className="italic text-clay">High-Signal Context.</span>
          </motion.h2>

          <motion.p
            custom={2}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="text-base md:text-lg max-w-xl mb-12 leading-relaxed font-sans"
          >
            Ingest, Filter, and Synthesize the global firehose of ArXiv papers,
            GitHub repos, and engineering blogs into a hyper-personalized,
            zero-noise intelligence feed.
          </motion.p>

          <motion.div
            custom={3}
            variants={fadeUpVariants}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
          >
            <button
              onClick={() => navigate("/onboarding")}
              className="flex items-center gap-4 px-8 py-4 bg-clay text-paper font-display uppercase tracking-wider text-sm font-bold border-2 border-clay transition-all duration-300 hover:bg-ink hover:border-ink hover:text-paper"
            >
              Start Pulsing →
            </button>
          </motion.div>
        </div>

        <div className="lg:col-span-3 p-6 flex flex-col font-mono text-xs">
          <div className="p-4 border border-ink bg-paper">
            <div className="flex justify-between items-center mb-4 border-b border-ink pb-2">
              <span className="font-bold">[/] GITHUB_REPO</span>
              <span className="text-clay font-bold">vLLM</span>
            </div>
            <div className="space-y-4">
              <div className="h-2 w-full border border-ink overflow-hidden p-[1px]">
                <motion.div
                  animate={{ width: ["0%", "100%", "0%"] }}
                  transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  className="h-full bg-ink"
                />
              </div>
              <p className="italic">
                Aggregating 124 open PRs for synthesis phase...
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
