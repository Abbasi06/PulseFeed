import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export default function CTA() {
  const navigate = useNavigate();

  return (
    <section className="relative z-10 w-full py-40 border-b-4 border-ink bg-paper font-sans">
      <div className="max-w-6xl mx-auto px-4 md:px-8 relative z-10 text-center">
        <div className="p-12 md:p-20 bg-paper border-4 border-ink">
          {/* Decorative tag */}
          <div className="absolute top-0 left-0 bg-ink text-paper text-xs font-mono font-bold px-3 py-1 uppercase tracking-widest">
            [!] ACTION REQUIRED // 001
          </div>

          <h2 className="text-4xl md:text-6xl font-display font-bold text-ink tracking-tighter uppercase mb-8 leading-[1]">
            <span className="text-clay italic">High-Signal Context</span> <br />
            Is The New Leverage.
          </h2>

          <p className="text-xs md:text-sm font-mono text-ink mb-12 max-w-2xl mx-auto leading-relaxed border-l-4 border-ink pl-4 text-left uppercase tracking-widest font-bold">
            Top engineers don't just write more code; they possess the
            architectural awareness to know exactly what is disrupting the
            stack. Secure your operational advantage.
          </p>

          <button
            onClick={() => navigate("/onboarding")}
            className="flex items-center gap-4 px-10 py-6 mx-auto bg-clay text-paper font-display uppercase tracking-wider text-sm font-bold border-2 border-clay transition-all duration-300 hover:bg-ink hover:border-ink hover:text-paper"
          >
            INITIALIZE YOUR SWARM →
          </button>

          <div className="mt-12 pt-6 border-t-2 border-ink border-dashed">
            <span className="text-[10px] text-ink font-mono font-bold tracking-[2px] uppercase">
              [→] Spend less time sifting. Build.
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
