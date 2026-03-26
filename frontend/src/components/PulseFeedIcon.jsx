/**
 * PulseFeedIcon
 *
 * An infinity symbol whose center crossing is replaced by an ECG heartbeat spike.
 * "Infinity that beats like a heartbeat."
 *
 * ViewBox 0 0 120 54 — right loop (x: 60→116), ECG spike at x≈60, left loop (x: 4→60).
 * The spike peaks at y=7 and troughs at y=47, slightly exceeding the loop bounds (y=10…44)
 * so it reads as a heartbeat bursting through the infinity shape.
 *
 * Props:
 *  size     — height in px; width is auto (120/54 ≈ 2.22× ratio)
 *  animated — true → traveling comet + pulse ring (use for loading screens)
 *           — false → static gradient path with gentle glow pulse (use for icons)
 *  color    — "auto"    → horizontal gradient #4C6E94 → #B7397A → #7c3aed
 *           — "white"   → white stroke (for use on dark gradient backgrounds)
 *  className
 */
import { useId } from "react";
import { motion } from "framer-motion";

// The combined infinity + ECG heartbeat path (single continuous stroke).
// Flow: center → right loop top → right loop bottom → flat → spike UP →
//       spike DOWN → baseline → left loop bottom → left loop top → center.
const PULSE_PATH =
  "M 60,27 C 64,10 116,10 116,27 C 116,44 64,44 65,27 L 62,27 L 60,7 L 58,47 L 55,27 C 56,44 4,44 4,27 C 4,10 56,10 60,27";

export default function PulseFeedIcon({
  size = 20,
  animated = false,
  color = "auto",
  className = "",
}) {
  // Unique IDs so multiple instances on the same page don't collide.
  const uid = useId().replace(/:/g, "x");
  const glowId = `pfx-glow-${uid}`;
  const gradId = `pfx-grad-${uid}`;
  const wGradId = `pfx-wgrad-${uid}`;

  const w = size * (120 / 54);

  const isWhite = color === "white";
  const ghostStroke = isWhite ? "rgba(255,255,255,0.25)" : "#1e293b";
  const staticStroke = isWhite ? `url(#${wGradId})` : `url(#${gradId})`;

  return (
    <svg
      viewBox="0 0 120 54"
      width={w}
      height={size}
      fill="none"
      className={className}
      style={{ overflow: "visible" }}
      aria-hidden="true"
    >
      <defs>
        {/* Glow filter — adds halo around bright strokes */}
        <filter id={glowId} x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="2.8" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Brand gradient — steel-blue → aurora-pink → violet */}
        <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#4C6E94" />
          <stop offset="45%" stopColor="#B7397A" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>

        {/* White-fade gradient — for use on coloured backgrounds */}
        <linearGradient id={wGradId} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgba(255,255,255,0.6)" />
          <stop offset="50%" stopColor="rgba(255,255,255,1)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0.6)" />
        </linearGradient>
      </defs>

      {/* ── Ghost trail ── always visible, dark/faint */}
      <path
        d={PULSE_PATH}
        stroke={ghostStroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {animated ? (
        /* ─────────────────────────────────────────────────────────────
           ANIMATED variant: comet + pulse ring
           Three-layer comet: wide soft ambient → mid tail → bright head
           Heartbeat ring fires when the comet reaches the ECG spike.
           ───────────────────────────────────────────────────────────── */
        <>
          {/* Layer 1 — wide violet ambient glow behind the comet */}
          <motion.path
            d={PULSE_PATH}
            stroke="#7c3aed"
            strokeWidth={10}
            strokeLinecap="round"
            opacity={0.08}
            style={{ pathLength: 0.38 }}
            animate={{ pathOffset: [0, 1] }}
            transition={{ duration: 2.8, ease: "linear", repeat: Infinity }}
          />

          {/* Layer 2 — pink mid-tail */}
          <motion.path
            d={PULSE_PATH}
            stroke="#B7397A"
            strokeWidth={3}
            strokeLinecap="round"
            opacity={0.35}
            filter={`url(#${glowId})`}
            style={{ pathLength: 0.22 }}
            animate={{ pathOffset: [0, 1] }}
            transition={{ duration: 2.8, ease: "linear", repeat: Infinity }}
          />

          {/* Layer 3 — bright white/pink comet head */}
          <motion.path
            d={PULSE_PATH}
            stroke="#fce7f3"
            strokeWidth={2.5}
            strokeLinecap="round"
            filter={`url(#${glowId})`}
            style={{ pathLength: 0.06 }}
            animate={{ pathOffset: [0, 1] }}
            transition={{ duration: 2.8, ease: "linear", repeat: Infinity }}
          />

          {/* Heartbeat pulse ring — expands from center when comet hits spike.
              Delay is tuned so it fires at ~75% of the loop duration
              (right loop is ~60% of path length, spike at ~72%). */}
          <motion.circle
            cx={60}
            cy={27}
            r={3}
            fill="none"
            stroke="#ec4899"
            strokeWidth={2}
            filter={`url(#${glowId})`}
            initial={{ opacity: 0, r: 3 }}
            animate={{
              r: [3, 28],
              opacity: [0.95, 0],
              strokeWidth: [2, 0.2],
            }}
            transition={{
              duration: 2.8,
              ease: "easeOut",
              repeat: Infinity,
              delay: 2.0,
            }}
          />

          {/* Secondary smaller ring for depth */}
          <motion.circle
            cx={60}
            cy={27}
            r={2}
            fill="none"
            stroke="#a855f7"
            strokeWidth={1.5}
            initial={{ opacity: 0 }}
            animate={{
              r: [2, 14],
              opacity: [0.7, 0],
            }}
            transition={{
              duration: 2.0,
              ease: "easeOut",
              repeat: Infinity,
              delay: 2.1,
            }}
          />
        </>
      ) : (
        /* ─────────────────────────────────────────────────────────────
           STATIC variant: full gradient path with gentle glow-pulse
           ───────────────────────────────────────────────────────────── */
        <motion.path
          d={PULSE_PATH}
          stroke={staticStroke}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          animate={{ opacity: [0.65, 1, 0.65] }}
          transition={{ duration: 2.4, ease: "easeInOut", repeat: Infinity }}
        />
      )}
    </svg>
  );
}
