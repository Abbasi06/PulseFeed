import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Plus, X } from "lucide-react";

// The chips the user can choose from
const PRESET_CHIPS = [
  "Artificial Intelligence", "Machine Learning", "Neural Networks", "NLP",
  "LLMs", "RAG", "Agentic Workflows", "Prompt Engineering", "Computer Vision",
  "Predictive Modeling", "Deep Learning", "Data Science", "Data Engineering",
  "Cloud Computing", "AWS", "Azure", "GCP", "Kubernetes", "Docker", "DevOps",
  "Software Engineering", "Full Stack Development", "Backend", "Frontend",
  "React", "Node.js", "Python", "Rust", "Go", "Cybersecurity", "Zero Trust",
  "OSINT", "Malware Analysis", "Penetration Testing", "Cryptography",
  "Blockchain", "Web3", "Smart Contracts", "DeFi", "Quantum Computing"
];

const CHIPS_REQUIRED = 5;

// Custom Chip Entry
function CustomChipEntry({ onAdd }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef(null);

  function openInput() {
    setOpen(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  function commit() {
    const trimmed = value.trim().slice(0, 30);
    if (trimmed) onAdd(trimmed);
    setValue("");
    setOpen(false);
  }

  function handleKey(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      commit();
    }
    if (e.key === "Escape") {
      setValue("");
      setOpen(false);
    }
  }

  if (open) {
    return (
      <div className="flex items-center gap-1 border border-white/20 liquid-glass rounded-full px-3 py-1.5 h-auto transition-all duration-300">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          onBlur={commit}
          placeholder="New interest..."
          className="text-sm text-off-white bg-transparent outline-none w-24 placeholder-white/40"
        />
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); setValue(""); setOpen(false); }}
          className="text-white/40 hover:text-white transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={openInput}
      className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium border border-dashed border-white/30 text-white/60 hover:border-white/60 hover:text-white transition-all duration-300 shadow-sm"
    >
      <Plus className="w-3.5 h-3.5" />
      Custom
    </button>
  );
}

export default function ChipSelection({ selectedChips, onChange }) {
  const selectedCount = selectedChips.length;
  const isComplete = selectedCount === CHIPS_REQUIRED;

  function toggleChip(label) {
    if (selectedChips.includes(label)) {
      onChange(selectedChips.filter((c) => c !== label));
    } else if (selectedCount < CHIPS_REQUIRED) {
      onChange([...selectedChips, label]);
    }
  }

  function addCustom(label) {
    if (!selectedChips.includes(label) && selectedCount < CHIPS_REQUIRED) {
      onChange([...selectedChips, label]);
    }
  }

  return (
    <div className="space-y-6 w-full max-w-2xl mx-auto font-sans">
      <div className="flex flex-col gap-1 items-start justify-between">
        <label className="text-lg font-bold text-off-white tracking-wide">
          Select Your Focus Areas
        </label>
        <div className="flex items-center justify-between w-full">
            <p className="text-sm text-white/50">
              Curate your intelligence feed by selecting exactly {CHIPS_REQUIRED} topics.
            </p>
            <span className={`text-sm font-bold tabular-nums ${isComplete ? 'text-mint-glow shadow-[0_0_10px_rgba(209,232,226,0.5)]' : 'text-white/50'}`}>
                {selectedCount} / {CHIPS_REQUIRED}
            </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden shadow-inner flex relative">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-aurora-pink to-mint-glow"
          initial={{ width: 0 }}
          animate={{
            width: `${(selectedCount / CHIPS_REQUIRED) * 100}%`,
          }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        {PRESET_CHIPS.map((chip) => {
          const isSelected = selectedChips.includes(chip);
          return (
            <motion.button
              key={chip}
              type="button"
              layout
              onClick={() => toggleChip(chip)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all duration-300 border ${
                isSelected
                  ? 'border-mint-glow/50 bg-mint-glow/10 text-mint-glow liquid-glass shadow-[0_0_15px_rgba(209,232,226,0.3)] scale-105'
                  : 'border-white/10 bg-white/5 text-white/70 hover:bg-white/10 hover:border-white/30 hover:text-white'
              }`}
            >
              {isSelected && (
                <span className="flex items-center justify-center w-4 h-4 bg-mint-glow/20 rounded-full">
                    <Check className="w-3 h-3 text-mint-glow" strokeWidth={3} />
                </span>
              )}
              {chip}
            </motion.button>
          );
        })}
        {/* Custom chips added by the user not in PRESET */}
        {selectedChips
          .filter((c) => !PRESET_CHIPS.includes(c))
          .map((chip) => (
            <motion.button
              key={chip}
              type="button"
              layout
              onClick={() => toggleChip(chip)}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold border border-mint-glow/50 bg-mint-glow/10 text-mint-glow liquid-glass shadow-[0_0_15px_rgba(209,232,226,0.3)] scale-105 transition-all duration-300"
            >
              <span className="flex items-center justify-center w-4 h-4 bg-mint-glow/20 rounded-full">
                  <Check className="w-3 h-3 text-mint-glow" strokeWidth={3} />
              </span>
              {chip}
            </motion.button>
          ))}
        
        {/* Only show custom input if not full */}
        <AnimatePresence>
            {!isComplete && (
                <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
                    <CustomChipEntry onAdd={addCustom} />
                </motion.div>
            )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mt-6 flex items-center justify-center gap-2 p-3 liquid-glass border border-mint-glow/30 rounded-xl bg-mint-glow/5 text-mint-glow shadow-[0_0_20px_rgba(209,232,226,0.15)]"
          >
            <Check className="w-5 h-5" />
            <span className="text-sm font-bold tracking-wide">Core parameters locked. Ready to synthesize.</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
