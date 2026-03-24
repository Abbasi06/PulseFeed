import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bot,
  Building2,
  Check,
  ChevronDown,
  Code2,
  FileSearch,
  FileText,
  Flame,
  FlaskConical,
  Github,
  Hash,
  Mail,
  MessageSquare,
  Newspaper,
  Plus,
  Search,
  Sparkles,
  TrendingUp,
  Twitter,
  Youtube,
} from "lucide-react";
import TagInput from "./TagInput";
import {
  ROLE_SUGGESTED_CREATORS,
  ROLE_SUGGESTED_SOURCES,
  SOURCE_CATEGORIES,
} from "../constants/sources";

const ICON_MAP = {
  Bot,
  Building2,
  Code2,
  FileSearch,
  FileText,
  Flame,
  FlaskConical,
  Github,
  Hash,
  Mail,
  MessageSquare,
  Newspaper,
  Search,
  Sparkles,
  TrendingUp,
  Twitter,
  Youtube,
};

function LucideIcon({ name, className }) {
  const Icon = ICON_MAP[name];
  return Icon ? <Icon className={className} /> : null;
}

// ---------------------------------------------------------------------------
// Source chip inside a category
// ---------------------------------------------------------------------------

function SourceCard({ source, selected, suggested, onToggle }) {
  return (
    <button
      type="button"
      onClick={() => onToggle(source.id)}
      className={`relative flex items-start gap-2.5 p-3 rounded-xl border text-left transition-all w-full ${
        selected
          ? "border-violet-500 bg-violet-500/8 ring-1 ring-violet-500/20"
          : "border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800"
      }`}
    >
      {suggested && !selected && (
        <span className="absolute -top-2 right-2 text-[9px] font-bold bg-amber-500 text-black px-1.5 py-0.5 rounded-full uppercase tracking-wide">
          Suggested
        </span>
      )}
      {selected && (
        <div className="absolute top-2 right-2 w-4 h-4 bg-violet-500 rounded-full flex items-center justify-center shrink-0">
          <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
        </div>
      )}
      <LucideIcon
        name={source.lucideIcon}
        className={`w-4 h-4 mt-0.5 shrink-0 ${selected ? "text-violet-400" : "text-slate-400"}`}
      />
      <div className="min-w-0 pr-4">
        <p
          className={`text-xs font-semibold ${selected ? "text-violet-300" : "text-slate-200"}`}
        >
          {source.label}
        </p>
        <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">
          {source.description}
        </p>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Category accordion
// ---------------------------------------------------------------------------

function CategorySection({
  category,
  open,
  onToggle,
  selectedSources,
  onToggleSource,
  suggestedIds,
}) {
  const selectedCount = category.sources.filter((s) =>
    selectedSources.includes(s.id),
  ).length;

  return (
    <div
      className={`rounded-xl border transition-colors ${
        open ? "border-slate-600" : "border-slate-800"
      }`}
    >
      {/* Header */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
      >
        <LucideIcon
          name={category.lucideIcon}
          className={`w-4 h-4 shrink-0 ${open ? "text-violet-400" : "text-slate-500"}`}
        />
        <div className="flex-1 min-w-0">
          <span
            className={`text-sm font-medium ${open ? "text-slate-200" : "text-slate-400"}`}
          >
            {category.label}
          </span>
          {!open && (
            <span className="ml-1.5 text-[10px] text-slate-600">
              {category.description}
            </span>
          )}
        </div>
        {selectedCount > 0 && (
          <span className="text-[10px] font-bold bg-violet-600 text-white px-1.5 py-0.5 rounded-full">
            {selectedCount}
          </span>
        )}
        <ChevronDown
          className={`w-4 h-4 text-slate-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Body — source grid */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 grid grid-cols-2 gap-2">
              {category.sources.map((source, i) => (
                <motion.div
                  key={source.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04, duration: 0.15 }}
                >
                  <SourceCard
                    source={source}
                    selected={selectedSources.includes(source.id)}
                    suggested={suggestedIds.includes(source.id)}
                    onToggle={onToggleSource}
                  />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Creator section
// ---------------------------------------------------------------------------

function CreatorSection({ field, creators, onCreatorsChange }) {
  const suggestions = ROLE_SUGGESTED_CREATORS[field] ?? [];

  function addCreator(name) {
    if (!creators.includes(name) && creators.length < 10) {
      onCreatorsChange([...creators, name]);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          Creators & Voices{" "}
          <span className="text-slate-500 font-normal">(optional)</span>
        </label>
        <p className="text-xs text-slate-500 mb-2">
          Add names or handles to bias your feed towards their content.
        </p>
        <TagInput
          tags={creators}
          onChange={onCreatorsChange}
          placeholder='e.g. Andrej Karpathy, Fireship…'
        />
      </div>

      {suggestions.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Quick add for your field
          </p>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((name) => {
              const added = creators.includes(name);
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => addCreator(name)}
                  disabled={added}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
                    added
                      ? "border-violet-500/40 bg-violet-500/10 text-violet-400 cursor-default"
                      : "border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-300"
                  }`}
                >
                  {added ? (
                    <Check className="w-2.5 h-2.5" />
                  ) : (
                    <Plus className="w-2.5 h-2.5" />
                  )}
                  {name}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main SourcePicker
// ---------------------------------------------------------------------------

export default function SourcePicker({
  field,
  sources,
  creators,
  onSourcesChange,
  onCreatorsChange,
}) {
  const [openCategories, setOpenCategories] = useState(() => {
    // Auto-open categories that have suggested sources for the current field
    const suggested = ROLE_SUGGESTED_SOURCES[field] ?? [];
    return SOURCE_CATEGORIES.filter((cat) =>
      cat.sources.some((s) => suggested.includes(s.id)),
    ).map((cat) => cat.id);
  });

  const suggestedIds = ROLE_SUGGESTED_SOURCES[field] ?? [];

  function toggleCategory(id) {
    setOpenCategories((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }

  function toggleSource(id) {
    onSourcesChange(
      sources.includes(id) ? sources.filter((s) => s !== id) : [...sources, id],
    );
  }

  const totalSelected = sources.length;

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-200 mb-1">
          Where should your feed pull from?
        </label>
        <p className="text-xs text-slate-500">
          Select sources — highlighted ones are recommended for your field.
          {totalSelected > 0 && (
            <span className="ml-1 text-violet-400 font-medium">
              {totalSelected} selected
            </span>
          )}
        </p>
      </div>

      {/* Category accordion */}
      <div className="space-y-2">
        {SOURCE_CATEGORIES.map((category) => (
          <CategorySection
            key={category.id}
            category={category}
            open={openCategories.includes(category.id)}
            onToggle={() => toggleCategory(category.id)}
            selectedSources={sources}
            onToggleSource={toggleSource}
            suggestedIds={suggestedIds}
          />
        ))}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3 pt-1">
        <div className="flex-1 h-px bg-slate-800" />
        <span className="text-[10px] text-slate-600 uppercase tracking-wider">
          Creator bias
        </span>
        <div className="flex-1 h-px bg-slate-800" />
      </div>

      {/* Creator input */}
      <CreatorSection
        field={field}
        creators={creators}
        onCreatorsChange={onCreatorsChange}
      />
    </div>
  );
}
