import { motion, useTime, useTransform } from "framer-motion";
import { Zap } from "lucide-react";

/**
 * Pulsar Component - Vintage Editorial Aesthetic
 *
 * Adapted for the print aesthetic: crisp concentric circles,
 * bold ink dashed lines, and stark clay snap accents.
 */

interface PulsarProps {
  size?: number;
  color?: "ink" | "clay";
  className?: string;
}

export default function Pulsar({
  size = 200,
  color = "ink",
  className = "",
}: PulsarProps) {
  const time = useTime();
  const rotate1 = useTransform(time, (t) => t * 0.05);
  const rotate2 = useTransform(time, (t) => t * -0.03);

  const colors = {
    ink: {
      primary: "var(--color-ink)",
      secondary: "var(--color-clay)",
      bg: "var(--color-paper)",
    },
    clay: {
      primary: "var(--color-clay)",
      secondary: "var(--color-ink)",
      bg: "var(--color-paper)",
    },
  }[color];

  return (
    <div
      className={`relative flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      {/* ── EXPANSION WAVES ── */}
      {[0, 1, 2].map((i) => (
        <motion.div
          key={`wave-${i}`}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{
            scale: [0.5, 2.2],
            opacity: [1, 0],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            delay: i * 1,
            ease: "linear",
          }}
          className="absolute inset-0 rounded-full border"
          style={{ borderColor: colors.primary, borderWidth: 1 }}
        />
      ))}

      {/* ── ACCRETION RINGS ── */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          rotate: rotate1,
          borderColor: colors.primary,
          borderWidth: 2,
          borderStyle: "dashed",
          scale: 0.85,
        }}
      />

      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          rotate: rotate2,
          borderColor: colors.secondary,
          borderWidth: 1,
          borderStyle: "dashed",
          scale: 1.1,
        }}
      />

      {/* ── CENTRAL CORE (Solid border, NO glow) ── */}
      <motion.div
        animate={{
          scale: [1, 1.05, 1],
        }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "linear",
        }}
        className="relative z-10 w-24 h-24 rounded-full flex items-center justify-center border-2 overflow-hidden"
        style={{ backgroundColor: colors.bg, borderColor: colors.primary }}
      >
        {/* Geometric crosshairs for central core detail */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30">
          <div
            className="w-full h-[1px] bg-current"
            style={{ color: colors.primary }}
          />
          <div
            className="absolute h-full w-[1px] bg-current"
            style={{ color: colors.primary }}
          />
        </div>

        <Zap
          size={32}
          className="relative z-20"
          style={{ color: colors.primary }}
        />
      </motion.div>

      {/* ── DATA NODES (Orbiting, Flat Geometry) ── */}
      <div className="absolute inset-0 pointer-events-none">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
          className="relative w-full h-full"
        >
          <div
            className="absolute top-[10%] left-1/2 -translate-x-1/2 w-2 h-2 rounded-none bg-current"
            style={{ color: colors.primary }}
          />
        </motion.div>

        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0"
        >
          {/* Triangular node */}
          <div
            className="absolute bottom-[15%] left-[20%] w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[8px]"
            style={{ borderBottomColor: colors.secondary }}
          />
        </motion.div>
      </div>
    </div>
  );
}
