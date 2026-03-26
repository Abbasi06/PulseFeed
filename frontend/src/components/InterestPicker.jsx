import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Brain, Check, Code2, Plus, Shield, X } from "lucide-react";
import { MIN_SUBFIELDS, ROLE_COLORS, ROLES } from "../constants/taxonomy";

const ROLE_ICONS = {
  "software-engineering": Code2,
  "ai-engineering": Brain,
  cybersecurity: Shield,
};

// ---------------------------------------------------------------------------
// Role Radio Card
// ---------------------------------------------------------------------------

function RoleCard({ role, selected, onSelect }) {
  const Icon = ROLE_ICONS[role.id];
  const colors = ROLE_COLORS[role.color];

  return (
    <button
      type="button"
      onClick={() => onSelect(role)}
      style={
        selected
          ? {
              boxShadow:
                "0 0 28px rgba(183,57,122,0.35), 0 0 60px rgba(76,110,148,0.18)",
            }
          : undefined
      }
      className={`flex-1 flex flex-col items-center gap-2 px-3 py-4 rounded-xl border transition-all text-center ${
        selected
          ? colors.card
          : "liquid-glass hover:border-white/25 hover:bg-white/[0.05]"
      }`}
    >
      <Icon
        className={`w-6 h-6 ${selected ? colors.cardIcon : "text-slate-400"}`}
      />
      <div>
        <p
          className={`text-sm font-semibold ${selected ? colors.cardLabel : "text-slate-300"}`}
        >
          {role.shortLabel}
        </p>
        <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">
          {role.description}
        </p>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Sub-field Chip
// ---------------------------------------------------------------------------

function SubChip({ label, selected, onToggle, colors }) {
  return (
    <button
      type="button"
      onClick={() => onToggle(label)}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
        selected
          ? colors.chip
          : "border-slate-700 bg-slate-800/60 text-slate-400 hover:border-slate-500 hover:text-slate-300"
      }`}
    >
      {selected && (
        <span
          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center shrink-0 ${colors.chipCheck}`}
        >
          <Check className="w-2 h-2 text-white" strokeWidth={3} />
        </span>
      )}
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Custom chip entry
// ---------------------------------------------------------------------------

function CustomChipEntry({ onAdd }) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef(null);

  function openInput() {
    setOpen(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  function commit() {
    const trimmed = value.trim().slice(0, 50);
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
      <div className="flex items-center gap-1 border border-slate-600 bg-slate-800 rounded-full px-2 py-1">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          onBlur={commit}
          placeholder="Type & press Enter…"
          className="text-xs text-slate-200 bg-transparent outline-none w-32 placeholder-slate-500"
        />
        <button
          type="button"
          onMouseDown={(e) => {
            e.preventDefault();
            setValue("");
            setOpen(false);
          }}
          className="text-slate-500 hover:text-slate-300"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={openInput}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-dashed border-slate-600 text-slate-400 hover:border-slate-400 hover:text-slate-300 transition-all"
    >
      <Plus className="w-3 h-3" />
      Add Custom
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main InterestPicker
// ---------------------------------------------------------------------------

export default function InterestPicker({
  field,
  subFields,
  onFieldChange,
  onSubFieldsChange,
}) {
  const activeRole = ROLES.find((r) => r.backendField === field) ?? null;
  const colors = activeRole
    ? ROLE_COLORS[activeRole.color]
    : ROLE_COLORS.violet;
  const selected = subFields.length;
  const ready = selected >= MIN_SUBFIELDS;

  function handleRoleSelect(role) {
    onFieldChange(role.backendField);
    onSubFieldsChange([]);
  }

  function toggleChip(label) {
    if (subFields.includes(label)) {
      onSubFieldsChange(subFields.filter((s) => s !== label));
    } else if (subFields.length < 10) {
      onSubFieldsChange([...subFields, label]);
    }
  }

  function addCustom(label) {
    if (!subFields.includes(label) && subFields.length < 10) {
      onSubFieldsChange([...subFields, label]);
    }
  }

  return (
    <div className="space-y-5">
      {/* Level 1 — Role cards */}
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          What do you build?
        </label>
        <p className="text-xs text-slate-500 mb-3">
          Pick your primary domain — this shapes every query your feed runs.
        </p>
        <div className="flex gap-2">
          {ROLES.map((role) => (
            <RoleCard
              key={role.id}
              role={role}
              selected={activeRole?.id === role.id}
              onSelect={handleRoleSelect}
            />
          ))}
        </div>
      </div>

      {/* Level 2 — Sub-field chips (only visible once a role is picked) */}
      <AnimatePresence mode="wait">
        {activeRole && (
          <motion.div
            key={activeRole.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-200">
                Pick your focus areas
              </label>
              <span
                className={`text-xs font-medium tabular-nums ${
                  ready ? "text-[#7C3AED]" : "text-slate-500"
                }`}
              >
                {selected} / {MIN_SUBFIELDS} minimum
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-1 w-full bg-slate-800 rounded-full mb-3 overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${colors.progress}`}
                initial={{ width: 0 }}
                animate={{
                  width: `${Math.min((selected / MIN_SUBFIELDS) * 100, 100)}%`,
                }}
                transition={{ duration: 0.25, ease: "easeOut" }}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {activeRole.subFields.map((sf) => (
                <SubChip
                  key={sf}
                  label={sf}
                  selected={subFields.includes(sf)}
                  onToggle={toggleChip}
                  colors={colors}
                />
              ))}
              {/* Custom chips added by the user */}
              {subFields
                .filter((sf) => !activeRole.subFields.includes(sf))
                .map((sf) => (
                  <SubChip
                    key={sf}
                    label={sf}
                    selected={true}
                    onToggle={toggleChip}
                    colors={colors}
                  />
                ))}
              <CustomChipEntry onAdd={addCustom} />
            </div>

            {ready && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-3 text-xs text-[#7C3AED] font-medium"
              >
                ✓ Great picks — you can select up to 10 total
              </motion.p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
