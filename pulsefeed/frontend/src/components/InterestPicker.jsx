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
  const colors = ROLE_COLORS.ink;

  return (
    <button
      type="button"
      onClick={() => onSelect(role)}
      className={`flex-1 flex flex-col items-center gap-2 px-3 py-4 rounded-none border-2 transition-none text-center interactive-snap ${
        selected ? colors.card : "border-ink bg-paper text-ink"
      }`}
    >
      <Icon className={`w-6 h-6 ${selected ? colors.cardIcon : "text-ink"}`} />
      <div>
        <p
          className={`text-sm font-display uppercase tracking-tight ${selected ? colors.cardLabel : "font-bold"}`}
        >
          {role.shortLabel}
        </p>
        <p className="text-[10px] font-mono mt-0.5 leading-tight">
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
      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase tracking-tight border-2 transition-none interactive-snap ${
        selected ? colors.chip : "border-ink bg-paper text-ink"
      }`}
    >
      {selected && (
        <span
          className={`w-3.5 h-3.5 flex items-center justify-center shrink-0 border border-ink bg-paper`}
        >
          <Check className="w-2 h-2 text-ink" strokeWidth={3} />
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
      <div className="flex items-center gap-1 border-2 border-ink bg-paper px-2 py-1">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          onBlur={commit}
          placeholder="TYPE & ENTER"
          className="text-xs font-mono text-ink bg-transparent outline-none w-32 placeholder-steel uppercase"
        />
        <button
          type="button"
          onMouseDown={(e) => {
            e.preventDefault();
            setValue("");
            setOpen(false);
          }}
          className="text-ink hover:text-clay interactive-snap p-1"
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
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase tracking-tight border-2 border-dashed border-ink text-ink bg-paper hover:border-solid interactive-snap"
    >
      <Plus className="w-3 h-3" />
      ADD CUSTOM
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
  const colors = ROLE_COLORS.ink;
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
    <div className="space-y-6">
      {/* Level 1 — Role cards */}
      <div className="p-6 border-b-2 border-ink">
        <label className="block text-2xl font-display font-bold text-ink uppercase mb-2">
          What do you build?
        </label>
        <p className="text-xs font-mono text-ink mb-6 max-w-sm uppercase">
          Select primary domain to initialize your swarm index parameters.
        </p>
        <div className="flex gap-4 flex-col sm:flex-row">
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
            className="p-6 pt-0"
          >
            <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-4 border-b border-ink pb-2">
              <label className="text-xl font-display font-bold text-ink uppercase">
                Vector Trajectories
              </label>
              <span
                className={`text-xs font-mono uppercase bg-paper border border-ink px-1 mt-2 sm:mt-0 ${
                  ready ? "text-clay border-clay font-bold" : "text-ink"
                }`}
              >
                {selected} / {MIN_SUBFIELDS} MAPPED
              </span>
            </div>

            {/* Progress bar (Print style) */}
            <div className="h-3 w-full border-2 border-ink bg-paper mb-6 overflow-hidden p-[1px] relative">
              <motion.div
                className={`h-full border-r-2 border-ink ${colors.progress}`}
                initial={{ width: 0 }}
                animate={{
                  width: `${Math.min((selected / MIN_SUBFIELDS) * 100, 100)}%`,
                }}
                transition={{ duration: 0.25, ease: "linear" }}
              />
            </div>

            <div className="flex flex-wrap gap-2 mb-6">
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
                className="text-xs font-mono font-bold text-clay uppercase border-l-2 border-clay pl-2"
              >
                [SYSTEM READY] Trajectories Confirmed.
              </motion.p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
