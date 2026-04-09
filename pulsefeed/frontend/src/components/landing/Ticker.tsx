import { motion } from "framer-motion";

const ROW_1 = [
  "ArXiv:2403.00123",
  "vLLM KV-Cache Improvements",
  "KEDA Autoscaling v2",
  "PyTorch 2.4 Release",
  "Flash Attention v3",
  "RAG Pipeline Patterns",
  "Quantization Methods",
  "MoE Token Routing",
  "LLM Inference at Scale",
  "Triton GPU Kernels",
  "OpenAI Responses API",
  "Gemini 2.5 Pro",
];

const ROW_2 = [
  "GitHub: vllm-project",
  "LangChain v0.3 Update",
  "Kubernetes 1.32 Notes",
  "Next.js 15 App Router",
  "Rust for ML Systems",
  "Speculative Decoding",
  "KV Cache Compression",
  "Distributed Training Tricks",
  "LoRA Fine-tuning Guide",
  "Ollama 0.6 Release",
  "DeepSeek-R2 Benchmarks",
  "Mistral 3B Architecture",
];

function TickerRow({
  items,
  direction = 1,
}: {
  items: string[];
  direction?: number;
}) {
  const duplicated = [...items, ...items, ...items];
  const duration = items.length * 3.5;

  return (
    <div className="overflow-hidden w-full">
      <motion.div
        className="flex whitespace-nowrap"
        animate={
          direction > 0 ? { x: ["0%", "-33.333%"] } : { x: ["-33.333%", "0%"] }
        }
        transition={{ duration, repeat: Infinity, ease: "linear" }}
      >
        {duplicated.map((item, i) => (
          <span key={i} className="inline-flex items-center shrink-0">
            <span className="px-5 font-mono text-[11px] uppercase tracking-[0.15em] text-ink font-bold">
              {item}
            </span>
            <span
              className="font-bold text-sm"
              style={{ color: "var(--color-clay)" }}
            >
              ✦
            </span>
          </span>
        ))}
      </motion.div>
    </div>
  );
}

export default function Ticker() {
  return (
    <section
      className="relative z-10 w-full bg-paper border-b-2 border-ink overflow-hidden font-sans select-none"
      aria-hidden="true"
    >
      {/* Row 1 — Ingesting */}
      <div className="flex items-stretch border-b border-ink">
        <div className="shrink-0 px-3 flex items-center justify-center border-r border-ink bg-ink text-paper">
          <span
            className="font-mono text-[8px] font-bold uppercase tracking-[0.25em]"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            Ingesting
          </span>
        </div>
        <div className="flex-1 py-2.5 bg-paper overflow-hidden">
          <TickerRow items={ROW_1} direction={1} />
        </div>
        <div className="shrink-0 px-3 flex items-center justify-center border-l border-ink bg-paper">
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1.2, repeat: Infinity }}
            className="w-2 h-2 bg-ink"
          />
        </div>
      </div>

      {/* Row 2 — Synthesized */}
      <div className="flex items-stretch">
        <div
          className="shrink-0 px-3 flex items-center justify-center border-r border-ink text-paper"
          style={{ background: "var(--color-clay)" }}
        >
          <span
            className="font-mono text-[8px] font-bold uppercase tracking-[0.25em]"
            style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          >
            Synthesized
          </span>
        </div>
        <div
          className="flex-1 py-2.5 overflow-hidden"
          style={{ background: "#F5F0E8" }}
        >
          <TickerRow items={ROW_2} direction={-1} />
        </div>
        <div
          className="shrink-0 px-3 flex items-center justify-center border-l border-ink"
          style={{ background: "#F5F0E8" }}
        >
          <motion.div
            animate={{ opacity: [1, 0, 1] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: 0.6 }}
            className="w-2 h-2"
            style={{ background: "var(--color-clay)" }}
          />
        </div>
      </div>
    </section>
  );
}
