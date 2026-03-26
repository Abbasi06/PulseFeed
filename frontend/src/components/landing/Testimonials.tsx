import { motion } from "framer-motion";

const testimonials = [
  {
    quote:
      "PulseFeed has completely replaced my morning Twitter scroll. It's the highest signal-to-noise ratio I've ever experienced.",
    author: "Sarah Jenkins",
    role: "ML Engineer",
  },
  {
    quote:
      "I used to spend 5 hours a week searching for relevant AI papers. Now they just show up in my feed.",
    author: "David Chen",
    role: "Ph.D. Researcher",
  },
  {
    quote:
      "The personalized synthesis is mind-blowing. It reads like a newsletter written by my smartest colleague.",
    author: "Elena Rodriguez",
    role: "Product Manager",
  },
  {
    quote:
      "We deployed PulseFeed for our entire engineering team and saw our internal knowledge sharing 10x overnight.",
    author: "Marcus Vance",
    role: "CTO",
  },
  {
    quote:
      "Finally, a tool that respects my time and intelligence. No clickbait, just pure knowledge.",
    author: "Dr. Amanda White",
    role: "Data Scientist",
  },
  {
    quote:
      "It's like having an army of research assistants reading the entire internet for me.",
    author: "James Oliver",
    role: "Tech Lead",
  },
];

export default function Testimonials() {
  return (
    <section className="relative w-full py-24 bg-[#010101] overflow-hidden font-sans border-t border-white/5">
      {/* Background radial glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-[#7c3aed]/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="container mx-auto px-6 max-w-7xl relative z-10">
        <div className="text-center mb-20">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            className="text-3xl md:text-5xl font-bold tracking-tight text-white mb-4"
          >
            Loved by builders
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ delay: 0.1 }}
            className="text-lg text-white/50"
          >
            Join thousands of professionals staying ahead of the curve.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonials.map((testimonial, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="p-8 rounded-3xl bg-[rgba(28,27,36,0.2)] border border-white/5 hover:bg-[rgba(28,27,36,0.4)] transition-colors duration-300 backdrop-blur-md"
            >
              <div className="flex gap-1 mb-6">
                {[...Array(5)].map((_, j) => (
                  <svg
                    key={j}
                    className="w-5 h-5 text-[#B7397A]"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                ))}
              </div>
              <p className="text-white/80 text-lg leading-relaxed mb-8">
                "{testimonial.quote}"
              </p>
              <div>
                <h4 className="font-bold text-white tracking-tight">
                  {testimonial.author}
                </h4>
                <p className="text-sm font-medium text-white/40">
                  {testimonial.role}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
