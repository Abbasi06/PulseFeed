/**
 * LandingPage — "Cognitive Evolution" theme
 *
 * Visual journey:
 *   Parchment (hero)  →  Midnight (benefits)  →  CTA
 *
 * Animations (Framer Motion):
 *   • SVG brain draws in via pathLength 0→1
 *   • Data nodes fly from edges to brain centre, then dissolve
 *   • Brain glows emerald after ingestion
 *   • Scroll drives parchment→dark crossfade
 *   • Benefits "Noise / Filter / Pulse" stagger in on scroll
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  motion,
  useInView,
  useScroll,
  useTransform,
  AnimatePresence,
} from "framer-motion";
import { ArrowRight, Zap } from "lucide-react";
import { useAuth } from "../context/AuthContext";

// ---------------------------------------------------------------------------
// SVG path data — Da Vinci-style brain (top view, two hemispheres)
// ViewBox: 0 0 400 300   Brain centre: (200, 150)
// ---------------------------------------------------------------------------

const P = {
  leftHemi: `
    M 200,46
    C 174,44 146,54 124,72
    C 102,90 88,116 88,144
    C 88,172 100,198 118,216
    C 136,234 160,246 184,250
    C 192,252 198,252 200,248
    L 200,46 Z
  `,
  rightHemi: `
    M 200,46
    C 226,44 254,54 276,72
    C 298,90 312,116 312,144
    C 312,172 300,198 282,216
    C 264,234 240,246 216,250
    C 208,252 202,252 200,248
    L 200,46 Z
  `,
  fissure: "M 200,46 L 200,250",
  cerebellum: `
    M 174,264 C 184,258 196,256 200,256 C 204,256 216,258 226,264
    C 235,270 238,280 233,286 C 226,292 214,296 200,296
    C 186,296 174,292 167,286 C 162,280 165,270 174,264 Z
  `,
  gyriLeft: [
    "M 136,74 C 154,62 174,60 192,68",
    "M 102,108 C 118,92 138,88 160,96",
    "M 94,140 C 112,124 134,120 156,128",
    "M 96,172 C 114,158 136,154 158,162",
    "M 106,202 C 124,190 144,188 166,196",
    "M 126,228 C 143,220 162,218 178,224",
  ],
  gyriRight: [
    "M 264,74 C 246,62 226,60 208,68",
    "M 298,108 C 282,92 262,88 240,96",
    "M 306,140 C 288,124 266,120 244,128",
    "M 304,172 C 286,158 264,154 242,162",
    "M 294,202 C 276,190 256,188 234,196",
    "M 274,228 C 257,220 238,216 222,224",
  ],
};

// ---------------------------------------------------------------------------
// Data nodes that fly into the brain
// dx/dy = starting offset from brain centre (200, 150)
// ---------------------------------------------------------------------------

const NODES = [
  {
    id: 1,
    dx: -260,
    dy: -120,
    label: "arxiv/2401.0412",
    color: "#10B981",
    delay: 0.2,
  },
  {
    id: 2,
    dx: 240,
    dy: -140,
    label: "nature.com/ml",
    color: "#60A5FA",
    delay: 0.7,
  },
  {
    id: 3,
    dx: -280,
    dy: 60,
    label: "github/llm-paper",
    color: "#F59E0B",
    delay: 1.2,
  },
  {
    id: 4,
    dx: 270,
    dy: 80,
    label: "hackernews/top",
    color: "#10B981",
    delay: 1.7,
  },
  {
    id: 5,
    dx: -90,
    dy: 190,
    label: "ieee/neural-arch",
    color: "#60A5FA",
    delay: 2.2,
  },
  {
    id: 6,
    dx: 100,
    dy: -210,
    label: "openai.com/research",
    color: "#F59E0B",
    delay: 2.7,
  },
];

// ---------------------------------------------------------------------------
// Brain SVG — draws in, then glows on ingestion
// ---------------------------------------------------------------------------

function BrainSVG({ glowing }) {
  const pathProps = (d, key) => ({
    key,
    d,
    fill: "none",
    stroke: glowing ? "#10B981" : "#7C6247",
    strokeWidth: glowing ? 1.2 : 0.9,
    strokeLinecap: "round",
    filter: glowing ? "url(#glow)" : undefined,
  });

  return (
    <svg
      viewBox="0 0 400 300"
      style={{ overflow: "visible", width: "100%", height: "100%" }}
      aria-label="Brain illustration"
    >
      <defs>
        <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-soft" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="12" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Ambient glow halo when active */}
      {glowing && (
        <motion.ellipse
          cx={200}
          cy={150}
          rx={130}
          ry={110}
          fill="rgba(16,185,129,0.06)"
          filter="url(#glow-soft)"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.8, 0.5], scale: [0.9, 1.05, 1] }}
          transition={{ duration: 2, ease: "easeOut" }}
        />
      )}

      {/* Left hemisphere */}
      <motion.path
        {...pathProps(P.leftHemi, "lh")}
        initial={{ pathLength: 0, opacity: 0.3 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 2.4, ease: [0.4, 0, 0.2, 1] }}
      />

      {/* Right hemisphere */}
      <motion.path
        {...pathProps(P.rightHemi, "rh")}
        initial={{ pathLength: 0, opacity: 0.3 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 2.4, ease: [0.4, 0, 0.2, 1], delay: 0.1 }}
      />

      {/* Interhemispheric fissure */}
      <motion.path
        {...pathProps(P.fissure, "fissure")}
        strokeOpacity={0.5}
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.8, ease: "easeOut", delay: 0.8 }}
      />

      {/* Cerebellum */}
      <motion.path
        {...pathProps(P.cerebellum, "cb")}
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 0.8 }}
        transition={{ duration: 1.4, ease: "easeOut", delay: 1.6 }}
      />

      {/* Left gyri */}
      {P.gyriLeft.map((d, i) => (
        <motion.path
          key={`gl${i}`}
          d={d}
          fill="none"
          stroke={glowing ? "#10B981" : "#7C6247"}
          strokeWidth={0.7}
          strokeOpacity={glowing ? 0.8 : 0.5}
          strokeLinecap="round"
          filter={glowing ? "url(#glow)" : undefined}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: "easeOut", delay: 1.2 + i * 0.12 }}
        />
      ))}

      {/* Right gyri */}
      {P.gyriRight.map((d, i) => (
        <motion.path
          key={`gr${i}`}
          d={d}
          fill="none"
          stroke={glowing ? "#10B981" : "#7C6247"}
          strokeWidth={0.7}
          strokeOpacity={glowing ? 0.8 : 0.5}
          strokeLinecap="round"
          filter={glowing ? "url(#glow)" : undefined}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: "easeOut", delay: 1.3 + i * 0.12 }}
        />
      ))}

      {/* Geometric overlay — circuit nodes that appear after ingestion */}
      {glowing && (
        <>
          {[
            [142, 100],
            [258, 100],
            [120, 155],
            [280, 155],
            [160, 210],
            [240, 210],
            [200, 75],
          ].map(([cx, cy], i) => (
            <motion.circle
              key={`node-${i}`}
              cx={cx}
              cy={cy}
              r={3}
              fill="#10B981"
              filter="url(#glow)"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 0.7, scale: 1 }}
              transition={{
                delay: 0.3 + i * 0.1,
                duration: 0.4,
                type: "spring",
              }}
            />
          ))}
          {/* Connection lines */}
          {[
            "M 142,100 L 200,75 L 258,100",
            "M 120,155 L 142,100",
            "M 280,155 L 258,100",
            "M 120,155 L 160,210",
            "M 280,155 L 240,210",
            "M 160,210 L 200,230 L 240,210",
          ].map((d, i) => (
            <motion.path
              key={`conn-${i}`}
              d={d}
              fill="none"
              stroke="#10B981"
              strokeWidth={0.5}
              strokeOpacity={0.4}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.6 + i * 0.12, duration: 0.6 }}
            />
          ))}
        </>
      )}

      {/* Data nodes flying in */}
      {NODES.map((n) => (
        <DataNode key={n.id} node={n} />
      ))}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Individual data node — flies from edge to brain centre, then dissolves
// ---------------------------------------------------------------------------

function DataNode({ node }) {
  // Brain centre in SVG coords
  const cx = 200;
  const cy = 150;

  return (
    <motion.g
      initial={{ x: node.dx, y: node.dy, opacity: 0, scale: 1 }}
      animate={{
        x: 0,
        y: 0,
        opacity: [0, 1, 1, 0],
        scale: [0.6, 1, 0.9, 0],
      }}
      transition={{
        delay: node.delay,
        duration: 1.8,
        times: [0, 0.15, 0.7, 1],
        ease: "easeInOut",
      }}
    >
      {/* The hexagon dot */}
      <circle cx={cx} cy={cy} r={5} fill={node.color} opacity={0.9} />
      <circle
        cx={cx}
        cy={cy}
        r={9}
        fill="none"
        stroke={node.color}
        strokeWidth={0.8}
        opacity={0.5}
      />
      {/* Trail line toward brain */}
      <motion.line
        x1={cx}
        y1={cy}
        x2={cx + node.dx * 0.5}
        y2={cy + node.dy * 0.5}
        stroke={node.color}
        strokeWidth={0.5}
        strokeOpacity={0.3}
        initial={{ pathLength: 1 }}
        animate={{ pathLength: 0 }}
        transition={{ delay: node.delay + 0.3, duration: 1 }}
      />
      {/* Label */}
      <text
        x={cx + (node.dx > 0 ? 14 : -14)}
        y={cy + 4}
        textAnchor={node.dx > 0 ? "start" : "end"}
        fontSize="7"
        fill={node.color}
        opacity={0.8}
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        {node.label}
      </text>
    </motion.g>
  );
}

// ---------------------------------------------------------------------------
// Hero section — parchment, brain, headline
// ---------------------------------------------------------------------------

function Hero() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [glowing, setGlowing] = useState(false);
  const heroRef = useRef(null);

  // Scroll-based darkening overlay on the hero
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const overlayOpacity = useTransform(scrollYProgress, [0, 0.8], [0, 1]);

  // Trigger glow after final node is ingested
  useEffect(() => {
    const lastNodeDone = NODES[NODES.length - 1].delay + 1.8;
    const timer = setTimeout(() => setGlowing(true), lastNodeDone * 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <section
      ref={heroRef}
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
      style={{ backgroundColor: "#F5F5DC", color: "#1a1a1a" }}
    >
      {/* Subtle parchment texture */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          backgroundSize: "200px 200px",
        }}
      />

      {/* Nav */}
      <nav className="absolute top-0 inset-x-0 flex items-center justify-between px-8 py-6 z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-[#1a1a1a] flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-[#F5F5DC]" />
          </div>
          <span
            style={{
              fontFamily: "'Cormorant Garamond', serif",
              fontWeight: 600,
              fontSize: "1.1rem",
              letterSpacing: "0.02em",
            }}
          >
            PulseBoard
          </span>
        </div>
        <button
          onClick={() =>
            navigate(isAuthenticated ? "/dashboard" : "/onboarding")
          }
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#1a1a1a]/30 text-sm font-medium hover:bg-[#1a1a1a] hover:text-[#F5F5DC] transition-colors duration-200"
          style={{ color: "#1a1a1a" }}
        >
          {isAuthenticated ? "Dashboard" : "Get Started"}
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </nav>

      {/* Brain scene */}
      <div
        className="relative z-0"
        style={{
          width: "min(460px, 90vw)",
          height: "min(380px, 75vw)",
          padding: "0 24px",
        }}
      >
        <BrainSVG glowing={glowing} />
      </div>

      {/* Headline — below brain */}
      <motion.div
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 text-center px-6 mt-8 max-w-3xl"
      >
        <h1
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontWeight: 300,
            fontSize: "clamp(2.4rem, 6vw, 4.2rem)",
            lineHeight: 1.12,
            letterSpacing: "-0.01em",
            color: "#1a1a1a",
          }}
        >
          Evolve Your Information Intake.
          <br />
          <em style={{ fontStyle: "italic", fontWeight: 400 }}>
            From Noise to Knowledge.
          </em>
        </h1>

        <p
          className="mt-5 text-base sm:text-lg leading-relaxed max-w-xl mx-auto"
          style={{ color: "#5a5244", fontFamily: "system-ui, sans-serif" }}
        >
          An AI Research Agent that filters the world's chaos into your personal
          power source — refreshed every 6 hours.
        </p>

        {/* Monospace stat row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="mt-6 flex items-center justify-center gap-8 flex-wrap"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "0.72rem",
            color: "#8B7355",
          }}
        >
          {[
            "10 hrs/week reclaimed",
            "Zero FOMO",
            "Gemini 2.5 · DuckDuckGo",
          ].map((s, i) => (
            <span key={i} className="flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-[#8B7355] inline-block" />
              {s}
            </span>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4, duration: 0.6 }}
          className="mt-10 flex items-center justify-center gap-4"
        >
          <button
            onClick={() =>
              navigate(isAuthenticated ? "/dashboard" : "/onboarding")
            }
            className="group inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl text-base font-semibold transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]"
            style={{
              background: "linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)",
              color: "#F5F5DC",
              boxShadow: "0 4px 24px rgba(26,26,26,0.2)",
            }}
          >
            {isAuthenticated ? "Open Dashboard" : "Begin Your Evolution"}
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </button>
          <span
            style={{
              fontSize: "0.8rem",
              color: "#8B7355",
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            no cost · no card
          </span>
        </motion.div>
      </motion.div>

      {/* Scroll darkening overlay */}
      <motion.div
        style={{ opacity: overlayOpacity, backgroundColor: "#0A0A0A" }}
        className="pointer-events-none absolute inset-0 z-20"
      />

      {/* Scroll hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 4, duration: 1 }}
        className="absolute bottom-8 z-10 flex flex-col items-center gap-2"
        style={{ color: "#8B7355" }}
      >
        <span
          style={{
            fontSize: "0.65rem",
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: "0.15em",
          }}
        >
          SCROLL
        </span>
        <motion.div
          animate={{ y: [0, 7, 0] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
          className="w-px h-8"
          style={{
            background: "linear-gradient(to bottom, #8B7355, transparent)",
          }}
        />
      </motion.div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Benefits — "The Noise / The Filter / The Pulse"
// ---------------------------------------------------------------------------

const BENEFITS = [
  {
    tag: "01 — The Noise",
    headline: "The internet produces 2.5 quintillion bytes daily.",
    body: "Your attention is finite. Scrolling LinkedIn, HackerNews, ArXiv, and Twitter for relevant updates costs the average knowledge worker 10 hours every week — and most of it is irrelevant noise.",
    visual: <NoiseVisual />,
    accent: "#EF4444",
  },
  {
    tag: "02 — The Filter",
    headline: "An agentic AI that hunts signal, not likes.",
    body: "PulseBoard deploys a research pipeline: parallel web searches, Gemini-powered synthesis, and a personalised ranking model tuned to your occupation and interests. The chaos becomes structured.",
    visual: <FilterVisual />,
    accent: "#10B981",
  },
  {
    tag: "03 — The Pulse",
    headline: "Reclaim 10 hours. End the FOMO.",
    body: "Every morning, open one tab. Your entire field — latest papers, industry moves, upcoming conferences — distilled to 2-sentence summaries. The experts in your domain synthesised for you.",
    visual: <PulseVisual />,
    accent: "#60A5FA",
  },
];

function NoiseVisual() {
  return (
    <div className="relative w-full h-40 flex flex-col justify-center gap-2 overflow-hidden">
      {[1, 0.6, 0.3, 0.7, 0.4, 0.8].map((op, i) => (
        <motion.div
          key={i}
          className="h-2.5 rounded"
          style={{
            width: `${55 + Math.sin(i * 1.7) * 30}%`,
            backgroundColor: `rgba(239,68,68,${op * 0.5})`,
            filter: `blur(${(1 - op) * 3}px)`,
            fontFamily: "'JetBrains Mono', monospace",
          }}
          animate={{
            opacity: [op, op * 0.4, op],
            x: [0, i % 2 === 0 ? 3 : -3, 0],
          }}
          transition={{
            duration: 2 + i * 0.3,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#0A0A0A]/20 to-transparent pointer-events-none" />
    </div>
  );
}

function FilterVisual() {
  return (
    <div className="relative w-full h-40 flex items-center justify-center">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border border-emerald-500/30"
          style={{ width: 60 + i * 44, height: 60 + i * 44 }}
          animate={{ scale: [1, 1.06, 1], opacity: [0.4, 0.7, 0.4] }}
          transition={{
            duration: 2.5,
            delay: i * 0.6,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
      <div className="w-10 h-10 rounded-full border border-emerald-500 bg-emerald-500/10 flex items-center justify-center">
        <Zap className="w-4 h-4 text-emerald-400" />
      </div>
      {/* Incoming dots */}
      {[0, 1, 2, 3].map((i) => {
        const angle = (i / 4) * Math.PI * 2;
        const r = 80;
        return (
          <motion.div
            key={`dot-${i}`}
            className="absolute w-1.5 h-1.5 rounded-full bg-emerald-400"
            initial={{
              x: Math.cos(angle) * r,
              y: Math.sin(angle) * r,
              opacity: 0,
            }}
            animate={{
              x: [Math.cos(angle) * r, Math.cos(angle) * 20, 0],
              y: [Math.sin(angle) * r, Math.sin(angle) * 20, 0],
              opacity: [0, 1, 0],
              scale: [1, 1, 0],
            }}
            transition={{
              duration: 2.4,
              delay: i * 0.6,
              repeat: Infinity,
              ease: "easeIn",
            }}
          />
        );
      })}
    </div>
  );
}

function PulseVisual() {
  const lines = [
    {
      w: "85%",
      bold: true,
      text: "AlphaFold 4 predicts protein folding at atomic precision.",
    },
    {
      w: "70%",
      bold: false,
      text: "Gemini 2.5 Flash sets new reasoning benchmark.",
    },
    { w: "60%", bold: false, text: "React 20 ships server actions natively." },
  ];
  return (
    <div className="w-full h-40 flex flex-col justify-center gap-4">
      {lines.map((l, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -12 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.2, duration: 0.5 }}
          className="flex items-start gap-3"
          style={{ width: l.w }}
        >
          <div className="mt-1.5 w-1 h-1 rounded-full bg-blue-400 shrink-0" />
          <p
            className={`text-xs leading-snug ${l.bold ? "text-slate-100 font-medium" : "text-slate-400"}`}
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            {l.text}
          </p>
        </motion.div>
      ))}
    </div>
  );
}

function BenefitSection({ benefit, index }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const isEven = index % 2 === 0;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={`flex flex-col ${isEven ? "md:flex-row" : "md:flex-row-reverse"} items-center gap-12 py-24 border-t border-white/5`}
    >
      {/* Text */}
      <div className="flex-1">
        <p
          className="mb-4 text-xs tracking-widest uppercase"
          style={{
            color: benefit.accent,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {benefit.tag}
        </p>
        <h2
          style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontWeight: 400,
            fontSize: "clamp(1.7rem, 3.5vw, 2.6rem)",
            lineHeight: 1.2,
            color: "#f1f5f9",
            letterSpacing: "-0.01em",
          }}
        >
          {benefit.headline}
        </h2>
        <p
          className="mt-5 text-sm leading-relaxed text-slate-400"
          style={{ maxWidth: "38ch" }}
        >
          {benefit.body}
        </p>
      </div>

      {/* Visual */}
      <div className="flex-1 w-full max-w-xs md:max-w-sm">
        <div
          className="w-full rounded-2xl p-6 border border-white/5"
          style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
        >
          {benefit.visual}
        </div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Marquee ticker
// ---------------------------------------------------------------------------

const TICKER = [
  "Gemini 2.5 Flash",
  "React Server Components",
  "Data Science Summit · Berlin",
  "AlphaFold 4",
  "Rust 2.0 Stable",
  "NeurIPS 2026",
  "Llama 4 Released",
  "PyTorch 3.0",
  "Google I/O 2026",
  "EU AI Act Enforcement",
];

function Ticker() {
  const doubled = [...TICKER, ...TICKER];
  return (
    <div
      className="py-5 overflow-hidden border-y"
      style={{
        borderColor: "rgba(255,255,255,0.06)",
        backgroundColor: "rgba(255,255,255,0.01)",
      }}
    >
      <p
        className="text-center mb-3 text-xs tracking-widest uppercase"
        style={{ color: "#4B5563", fontFamily: "'JetBrains Mono', monospace" }}
      >
        Current Pulse
      </p>
      <div className="relative overflow-hidden">
        <motion.div
          animate={{ x: ["0%", "-50%"] }}
          transition={{ repeat: Infinity, duration: 30, ease: "linear" }}
          className="flex gap-10 whitespace-nowrap w-max"
        >
          {doubled.map((item, i) => (
            <span
              key={i}
              className="text-sm text-slate-500 flex items-center gap-2.5"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "0.72rem",
              }}
            >
              <span className="w-1 h-1 rounded-full bg-emerald-700 inline-block" />
              {item}
            </span>
          ))}
        </motion.div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CTA
// ---------------------------------------------------------------------------

function CTASection() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section
      ref={ref}
      className="py-40 px-6 flex flex-col items-center text-center relative overflow-hidden"
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 50% 35% at 50% 60%, rgba(16,185,129,0.06) 0%, transparent 100%)",
        }}
      />
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        className="mb-5 text-xs tracking-widest uppercase"
        style={{ color: "#10B981", fontFamily: "'JetBrains Mono', monospace" }}
      >
        Your evolution begins
      </motion.p>
      <motion.h2
        initial={{ opacity: 0, y: 24 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ delay: 0.08, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontWeight: 300,
          fontSize: "clamp(2.4rem, 6vw, 4.5rem)",
          lineHeight: 1.1,
          letterSpacing: "-0.01em",
          color: "#f1f5f9",
        }}
      >
        Stop scrolling.
        <br />
        <em style={{ fontStyle: "italic", color: "#10B981" }}>
          Start pulsing.
        </em>
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: 16 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="mt-6 max-w-sm text-slate-500"
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: "0.8rem",
        }}
      >
        Tell us who you are. The agent handles the rest.
      </motion.p>
      <motion.button
        initial={{ opacity: 0, scale: 0.9 }}
        animate={inView ? { opacity: 1, scale: 1 } : {}}
        transition={{ delay: 0.32, type: "spring", stiffness: 180 }}
        onClick={() => navigate(isAuthenticated ? "/dashboard" : "/onboarding")}
        className="mt-10 group inline-flex items-center gap-3 px-8 py-4 rounded-xl text-lg font-semibold transition-all duration-200 hover:scale-[1.04] active:scale-[0.97]"
        style={{
          background: "linear-gradient(135deg, #065F46 0%, #10B981 100%)",
          color: "#fff",
          boxShadow: "0 0 40px rgba(16,185,129,0.2)",
        }}
      >
        {isAuthenticated ? "Open My Dashboard" : "Build My Feed"}
        <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
      </motion.button>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export default function LandingPage() {
  // Force parchment on body while on this page; restore on unmount
  useEffect(() => {
    const prev = document.body.style.backgroundColor;
    document.body.style.backgroundColor = "#F5F5DC";
    return () => {
      document.body.style.backgroundColor = prev;
    };
  }, []);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F5F5DC" }}>
      {/* Hero — parchment */}
      <Hero />

      {/* Benefits + rest — midnight dark */}
      <div style={{ backgroundColor: "#0A0A0A" }}>
        <div className="max-w-5xl mx-auto px-6">
          {BENEFITS.map((b, i) => (
            <BenefitSection key={b.tag} benefit={b} index={i} />
          ))}
        </div>

        <Ticker />
        <CTASection />

        {/* Footer */}
        <footer
          className="py-10 px-6 border-t flex items-center justify-between text-xs"
          style={{
            borderColor: "rgba(255,255,255,0.05)",
            color: "#374151",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md bg-emerald-900/50 border border-emerald-800/50 flex items-center justify-center">
              <Zap className="w-3 h-3 text-emerald-500" />
            </div>
            <span>PulseBoard</span>
          </div>
          <span>Gemini · FastAPI · React · Framer Motion</span>
        </footer>
      </div>
    </div>
  );
}
