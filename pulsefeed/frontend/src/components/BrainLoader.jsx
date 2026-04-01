/**
 * BrainLoader — loading overlay shown while AI feed is generating / refreshing.
 * Uses the PulseFeedIcon animated variant (infinity + heartbeat comet).
 */
import { motion } from "framer-motion";
import PulseFeedIcon from "./PulseFeedIcon";

export default function BrainLoader({ message = "Researching your feed…" }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center py-20 gap-8">
      {/* Animated infinity-heartbeat icon */}
      <div className="relative flex items-center justify-center">
        {/* Ambient background bloom */}
        <div
          className="absolute rounded-full pointer-events-none"
          style={{
            width: 200,
            height: 90,
            background:
              "radial-gradient(ellipse at center, rgba(183,57,122,0.12) 0%, rgba(124,58,237,0.08) 50%, transparent 70%)",
            filter: "blur(12px)",
          }}
        />
        <PulseFeedIcon size={80} animated />
      </div>

      {/* Brand + message */}
      <div className="text-center space-y-2.5">
        <motion.p
          className="text-base font-bold tracking-tight text-white"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          Pulse<span className="text-violet-400">Feed</span>
        </motion.p>

        <motion.p
          className="text-sm text-slate-400"
          style={{ fontFamily: "'JetBrains Mono', monospace" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          {message}
        </motion.p>

        {/* Dot pulse indicator */}
        <motion.div
          className="flex items-center justify-center gap-2 pt-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-violet-500/60"
              animate={{ opacity: [0.25, 1, 0.25], scale: [0.8, 1.3, 0.8] }}
              transition={{
                duration: 1.4,
                delay: i * 0.28,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          ))}
        </motion.div>
      </div>
    </div>
  );
}
