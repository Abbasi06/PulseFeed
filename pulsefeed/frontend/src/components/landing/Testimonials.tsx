import { motion } from "framer-motion";

const testimonials = [
  {
    quote:
      "PulseFeed replaced my entire morning research routine. The signal-to-noise ratio is unlike anything else I've used.",
    author: "Sarah Jenkins",
    role: "ML Engineer",
    tag: "[T.01]",
  },
  {
    quote:
      "I used to spend five hours a week hunting ArXiv. Now the right papers just show up — summarized and ready.",
    author: "David Chen",
    role: "PhD Researcher",
    tag: "[T.02]",
  },
  {
    quote:
      "It reads like a newsletter written by my smartest colleague. Except it covers everything, every day.",
    author: "Elena Rodriguez",
    role: "Staff Engineer",
    tag: "[T.03]",
  },
  {
    quote:
      "We rolled it out to the full engineering team. Internal knowledge sharing went through the roof overnight.",
    author: "Marcus Vance",
    role: "CTO",
    tag: "[T.04]",
  },
  {
    quote:
      "Finally a tool that respects my time and intelligence. Zero clickbait. Just architecture and signal.",
    author: "Dr. Amanda White",
    role: "Data Scientist",
    tag: "[T.05]",
  },
  {
    quote:
      "It's like having an army of research assistants reading the entire technical internet — and distilling it.",
    author: "James Oliver",
    role: "Tech Lead",
    tag: "[T.06]",
  },
];

export default function Testimonials() {
  return (
    <section className="relative z-10 w-full bg-paper font-sans border-b-4 border-ink">
      {/* Section header */}
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-16 md:py-20 border-b-2 border-ink">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 border border-ink mb-6 bg-paper">
              <span className="text-[11px] font-mono font-bold tracking-widest uppercase text-ink">
                [/] Field Reports
              </span>
            </div>
            <h2 className="text-4xl md:text-6xl lg:text-7xl font-display font-bold tracking-tighter text-ink uppercase leading-[0.9]">
              Trusted by <br />
              <span className="italic text-clay">Engineers.</span>
            </h2>
          </div>
          <p className="font-mono text-xs uppercase tracking-widest text-ink max-w-xs leading-relaxed border-l-2 border-ink pl-4">
            6 field reports from engineers and researchers who eliminated manual
            research entirely.
          </p>
        </div>
      </div>

      {/* 3×2 testimonial grid */}
      <div className="max-w-6xl mx-auto px-4 md:px-8">
        <div className="border-x-2 border-b-2 border-ink">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-ink">
            {testimonials.map((t, i) => (
              <motion.div
                key={t.tag}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{
                  duration: 0.7,
                  delay: (i % 3) * 0.1,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="bg-paper p-8 lg:p-10 flex flex-col gap-6 group hover:bg-ink transition-none cursor-default"
              >
                {/* Tag + large quote mark */}
                <div className="flex items-start justify-between">
                  <span className="text-[10px] font-mono font-bold tracking-widest text-clay uppercase">
                    {t.tag}
                  </span>
                  <span
                    className="text-5xl font-display font-bold leading-none text-ink/10 group-hover:text-paper/10 select-none"
                    aria-hidden="true"
                  >
                    "
                  </span>
                </div>

                {/* Quote */}
                <p className="text-[13px] md:text-sm font-sans leading-relaxed text-ink group-hover:text-paper flex-1">
                  "{t.quote}"
                </p>

                {/* Author */}
                <div className="border-t border-ink group-hover:border-paper/20 pt-4">
                  <div className="font-display font-bold text-sm uppercase tracking-tight text-ink group-hover:text-paper">
                    {t.author}
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-ink/50 group-hover:text-paper/50 mt-0.5">
                    {t.role}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom strip */}
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 border-t-0">
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-3 h-3 border border-ink"
                style={{
                  background: i < 5 ? "var(--color-clay)" : "transparent",
                }}
              />
            ))}
          </div>
          <span className="font-mono text-[10px] uppercase tracking-widest text-ink/50 font-bold">
            5.0 avg · 200+ field engineers
          </span>
        </div>
      </div>
    </section>
  );
}
