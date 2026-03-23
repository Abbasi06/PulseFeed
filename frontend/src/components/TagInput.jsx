import { useState } from "react";

export default function TagInput({
  tags,
  onChange,
  placeholder = "Add tag…",
  maxTags = 10,
}) {
  const [input, setInput] = useState("");

  function addTag(raw) {
    const value = raw.trim().slice(0, 50);
    if (!value) return;
    if (tags.length >= maxTags) return;
    if (tags.some((t) => t.toLowerCase() === value.toLowerCase())) return;
    onChange([...tags, value]);
  }

  function handleKey(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(input);
      setInput("");
    } else if (e.key === "Backspace" && input === "" && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  function removeTag(index) {
    onChange(tags.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-wrap gap-2 p-2.5 bg-slate-800 border border-slate-700 rounded-lg focus-within:border-violet-500 focus-within:ring-1 focus-within:ring-violet-500/30 transition-colors min-h-[44px]">
      {tags.map((tag, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-violet-500/15 text-violet-300 text-sm rounded-md border border-violet-500/30"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(i)}
            className="text-violet-400 hover:text-white transition-colors leading-none"
            aria-label={`Remove ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKey}
        onBlur={() => {
          if (input) {
            addTag(input);
            setInput("");
          }
        }}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[120px] bg-transparent text-sm text-slate-200 placeholder-slate-500 outline-none"
      />
    </div>
  );
}
