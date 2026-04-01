import { useMemo } from "react";
import { motion } from "framer-motion";

const PARTICLE_COUNT = 55;

export default function ParticleField() {
  const particles = useMemo(
    () =>
      Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: 1.5 + Math.random() * 2,
        color: Math.random() > 0.5 ? "#B7397A" : "#D1E8E2",
        opacity: 0.25 + Math.random() * 0.45,
        driftX: (Math.random() - 0.5) * 50,
        driftY: (Math.random() - 0.5) * 50,
        duration: 14 + Math.random() * 18,
        // Negative delay starts each particle mid-cycle so they don't all move in sync
        delay: -(Math.random() * 25),
      })),
    [],
  );

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      {/* Ambient glow blobs */}
      <div className="absolute top-[-5%] left-1/2 -translate-x-1/2 w-[700px] h-[450px] rounded-full bg-[#B7397A]/10 blur-[120px]" />
      <div className="absolute top-[40%] left-[10%] w-[400px] h-[300px] rounded-full bg-[#7c3aed]/8 blur-[100px]" />
      <div className="absolute top-[30%] right-[5%] w-[450px] h-[320px] rounded-full bg-[#4C6E94]/10 blur-[100px]" />
      <div className="absolute bottom-[10%] left-[30%] w-[500px] h-[350px] rounded-full bg-[#B7397A]/6 blur-[110px]" />

      {/* Particles — framer-motion uses WAAPI for transform/opacity: compositor-threaded */}
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            backgroundColor: p.color,
            boxShadow: `0 0 ${p.size * 3}px ${p.color}80`,
            willChange: "transform",
          }}
          animate={{
            x: [0, p.driftX, 0],
            y: [0, p.driftY, 0],
            opacity: [p.opacity, p.opacity * 0.4, p.opacity],
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}
