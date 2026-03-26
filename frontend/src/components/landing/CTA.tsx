import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";

export default function CTA() {
  const navigate = useNavigate();

  return (
    <section className="relative w-full py-48 bg-[#010101] overflow-hidden font-sans border-t border-white/5">
      {/* Background glow and gradient */}
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none mix-blend-overlay z-0" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br from-[#B7397A]/20 via-[#7c3aed]/20 to-[#4C6E94]/20 blur-[120px] rounded-full pointer-events-none z-0" />

      <div className="container mx-auto px-6 max-w-4xl relative z-10 text-center">
        <motion.div
          initial={{ opacity: 0, y: 100, scale: 0.9 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ 
            duration: 1.2, 
            ease: [0.16, 1, 0.3, 1] 
          }}
          className="p-10 md:p-20 rounded-[3rem] bg-[rgba(28,27,36,0.3)] border border-white/10 shadow-[0_0_50px_rgba(183,57,122,0.1)] backdrop-blur-2xl relative overflow-hidden"
        >
          {/* Inner glow */}
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />

          <h2 className="text-4xl md:text-6xl font-bold tracking-tighter text-white mb-8 leading-[1]">
            The Secret to 10X Engineering is <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#B7397A] via-[#7c3aed] to-[#4C6E94] italic px-2">
              High-Signal Context.
            </span>
          </h2>

          <p className="text-lg md:text-xl text-white/40 mb-12 max-w-3xl mx-auto leading-relaxed">
            The industry's leading engineers don't just write more code; they possess the 
            situational awareness to know exactly what architectures are disrupting the 
            stack right now. PulseFeed gives you that advantage.
          </p>

          <div className="flex justify-center relative group w-max mx-auto">
            <div className="absolute -inset-[3px] bg-gradient-to-r from-[#B7397A]/40 to-[#4C6E94]/40 rounded-full blur-sm opacity-50 group-hover:opacity-100 transition duration-500" />
            <div className="absolute -inset-[1px] bg-gradient-to-r from-[#B7397A]/60 to-[#4C6E94]/60 rounded-full" />

            <button
              onClick={() => navigate("/onboarding")}
              className="relative flex items-center gap-4 px-10 py-5 bg-white rounded-full text-black font-bold text-lg hover:scale-[1.02] transition-transform duration-300"
            >
              Initialize Your Swarm
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-tr from-[#B7397A] to-[#4C6E94]">
                <ArrowRight size={16} className="text-white shrink-0" />
              </div>
            </button>
          </div>

          <p className="mt-8 text-[10px] text-white/20 tracking-[2px] font-bold uppercase">
             Spend less time sifting. Spend more time building.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
