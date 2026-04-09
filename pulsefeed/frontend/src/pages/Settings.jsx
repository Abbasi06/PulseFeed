import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Atom,
  BarChart2,
  BookOpen,
  Bot,
  Brain,
  Check,
  Cloud,
  Code2,
  FileText,
  HelpCircle,
  Link,
  Newspaper,
  Palette,
  Rss,
  Shield,
  LogOut,
  Save,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import TagInput from "../components/TagInput";
import { API_URL } from "../config";

const FIELDS = [
  { id: "AI & Machine Learning", label: "AI & ML", icon: Brain },
  { id: "Software Engineering", label: "Software Eng.", icon: Code2 },
  { id: "Cybersecurity", label: "Cybersecurity", icon: Shield },
  { id: "Data Science", label: "Data Science", icon: BarChart2 },
  { id: "Cloud & DevOps", label: "Cloud & DevOps", icon: Cloud },
  { id: "Blockchain & Web3", label: "Blockchain", icon: Link },
  { id: "Product & Design", label: "Product & Design", icon: Palette },
  { id: "Quantum Computing", label: "Quantum", icon: Atom },
  { id: "Robotics & Embedded", label: "Robotics", icon: Bot },
  { id: "Other", label: "Other", icon: HelpCircle },
];

const SUB_FIELD_PLACEHOLDER = {
  "AI & Machine Learning": "e.g. LLMs, Computer Vision, RL…",
  "Software Engineering": "e.g. Backend, Frontend, APIs…",
  Cybersecurity: "e.g. Zero Trust, Pen Testing, OSINT…",
  "Data Science": "e.g. NLP, Time Series, Visualisation…",
  "Cloud & DevOps": "e.g. Kubernetes, Terraform, CI/CD…",
  "Blockchain & Web3": "e.g. DeFi, Smart Contracts, L2…",
  "Product & Design": "e.g. UX Research, Design Systems…",
  "Quantum Computing": "e.g. Quantum Algorithms, Qubits…",
  "Robotics & Embedded": "e.g. ROS, Microcontrollers…",
  Other: "e.g. specific topics you care about…",
};

const FORMAT_CARDS = [
  {
    id: "Research Papers",
    label: "Research Papers",
    desc: "ArXiv · DeepMind · OpenAI",
    icon: FileText,
  },
  {
    id: "Technical Articles",
    label: "Tech Articles",
    desc: "Medium · Dev.to · Hashnode",
    icon: Newspaper,
  },
  {
    id: "Books & Guides",
    label: "Books & Guides",
    desc: "O'Reilly · Manning · Roadmaps",
    icon: BookOpen,
  },
  {
    id: "Engineering Blogs",
    label: "Eng. Blogs",
    desc: "Netflix · Uber · Meta Infra",
    icon: Rss,
  },
];

const MAX_NAME = 100;
const MAX_OCC = 150;

function SectionHeader({ label }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-[10px] font-mono font-bold tracking-[0.2em] uppercase text-text-secondary">
        {label}
      </span>
      <div
        className="flex-1 h-px"
        style={{ background: "rgba(90,45,160,0.25)" }}
      />
    </div>
  );
}

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const userId = user?.id;

  const [name, setName] = useState("");
  const [occupation, setOccupation] = useState("");
  const [field, setField] = useState("");
  const [subFields, setSubFields] = useState([]);
  const [preferredFormats, setPreferredFormats] = useState([]);
  const [refreshInterval, setRefreshInterval] = useState(6);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!userId) return;
    fetch(`${API_URL}/users/${userId}`, { credentials: "include" })
      .then((r) => r.json())
      .then((u) => {
        setName(u.name ?? "");
        setOccupation(u.occupation ?? "");
        setField(u.field ?? "");
        setSubFields(u.sub_fields ?? []);
        setPreferredFormats(u.preferred_formats ?? []);
        setRefreshInterval(u.refresh_interval_hours ?? 6);
      })
      .catch(() => setApiError("Could not load your profile."))
      .finally(() => setFetching(false));
  }, [userId]);

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Name is required";
    if (!occupation.trim()) e.occupation = "Occupation is required";
    if (!field) e.field = "Select your primary field";
    if (subFields.length === 0) e.subFields = "Add at least one area of focus";
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length) {
      setErrors(e2);
      return;
    }
    setErrors({});
    setApiError("");
    setSaved(false);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/users/${userId}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          occupation: occupation.trim(),
          field,
          sub_fields: subFields,
          preferred_formats: preferredFormats,
          refresh_interval_hours: refreshInterval,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setApiError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full"
              style={{ background: "var(--color-deep-purple)" }}
              animate={{ scale: [1, 1.6, 1], opacity: [0.4, 1, 0.4] }}
              transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.18 }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      className="max-w-2xl mx-auto px-5 sm:px-8 py-10 font-sans"
      style={{ color: "var(--color-text-primary)" }}
    >
      {/* Header */}
      <div
        className="mb-8 pb-6"
        style={{ borderBottom: "1px solid rgba(90,45,160,0.25)" }}
      >
        <h2 className="text-2xl font-display font-bold tracking-tight uppercase">
          Profile Settings
        </h2>
        <p
          className="mt-1 text-xs font-mono tracking-widest uppercase"
          style={{ color: "var(--color-text-secondary)" }}
        >
          [/] Update your context to re-tune the swarm
        </p>
      </div>

      {/* Banners */}
      <AnimatePresence>
        {apiError && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-start gap-3 px-4 py-3 mb-6 rounded-lg"
            style={{
              background: "rgba(255,45,122,0.1)",
              border: "1px solid rgba(255,45,122,0.25)",
            }}
          >
            <span
              className="text-sm shrink-0 mt-0.5"
              style={{ color: "var(--color-neon-pink)" }}
            >
              ⚠
            </span>
            <p className="text-sm" style={{ color: "var(--color-neon-pink)" }}>
              {apiError}
            </p>
          </motion.div>
        )}
        {saved && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2 px-4 py-3 mb-6 rounded-lg"
            style={{
              background: "rgba(0,212,255,0.08)",
              border: "1px solid rgba(0,212,255,0.2)",
            }}
          >
            <Check
              className="w-4 h-4 shrink-0"
              style={{ color: "var(--color-neon-cyan)" }}
            />
            <p
              className="text-sm font-medium"
              style={{ color: "var(--color-neon-cyan)" }}
            >
              Profile saved — swarm is re-tuning.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} noValidate className="space-y-8">
        {/* Identity */}
        <div>
          <SectionHeader label="[01] Identity" />
          <div className="space-y-4">
            {/* Name */}
            <div>
              <div className="flex justify-between mb-2">
                <label
                  className="text-xs font-mono font-bold uppercase tracking-widest"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  Name
                </label>
                <span
                  className={`text-[10px] font-mono font-bold ${name.length > MAX_NAME * 0.9 ? "" : ""}`}
                  style={{
                    color:
                      name.length > MAX_NAME * 0.9
                        ? "var(--color-neon-pink)"
                        : "var(--color-text-secondary)",
                  }}
                >
                  {name.length}/{MAX_NAME}
                </span>
              </div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, MAX_NAME))}
                placeholder="Ada Lovelace"
                className="w-full px-4 py-2.5 text-sm font-sans outline-none transition-all"
                style={{
                  background: "rgba(13,11,24,0.6)",
                  border: errors.name
                    ? "1px solid var(--color-neon-pink)"
                    : "1px solid rgba(90,45,160,0.3)",
                  borderRadius: "0.5rem",
                  color: "var(--color-text-primary)",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "var(--color-neon-cyan)")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = errors.name
                    ? "var(--color-neon-pink)"
                    : "rgba(90,45,160,0.3)")
                }
              />
              {errors.name && (
                <p
                  className="mt-1.5 text-[11px] font-mono"
                  style={{ color: "var(--color-neon-pink)" }}
                >
                  {errors.name}
                </p>
              )}
            </div>

            {/* Occupation */}
            <div>
              <div className="flex justify-between mb-2">
                <label
                  className="text-xs font-mono font-bold uppercase tracking-widest"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  Role / Title
                </label>
                <span
                  className="text-[10px] font-mono font-bold"
                  style={{
                    color:
                      occupation.length > MAX_OCC * 0.9
                        ? "var(--color-neon-pink)"
                        : "var(--color-text-secondary)",
                  }}
                >
                  {occupation.length}/{MAX_OCC}
                </span>
              </div>
              <input
                type="text"
                value={occupation}
                onChange={(e) =>
                  setOccupation(e.target.value.slice(0, MAX_OCC))
                }
                placeholder="Chief Systems Architect"
                className="w-full px-4 py-2.5 text-sm font-sans outline-none transition-all"
                style={{
                  background: "rgba(13,11,24,0.6)",
                  border: errors.occupation
                    ? "1px solid var(--color-neon-pink)"
                    : "1px solid rgba(90,45,160,0.3)",
                  borderRadius: "0.5rem",
                  color: "var(--color-text-primary)",
                }}
                onFocus={(e) =>
                  (e.currentTarget.style.borderColor = "var(--color-neon-cyan)")
                }
                onBlur={(e) =>
                  (e.currentTarget.style.borderColor = errors.occupation
                    ? "var(--color-neon-pink)"
                    : "rgba(90,45,160,0.3)")
                }
              />
              {errors.occupation && (
                <p
                  className="mt-1.5 text-[11px] font-mono"
                  style={{ color: "var(--color-neon-pink)" }}
                >
                  {errors.occupation}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Primary Field */}
        <div>
          <SectionHeader label="[02] Primary Domain" />
          <div className="flex flex-wrap gap-2">
            {FIELDS.map((f) => {
              const Icon = f.icon;
              const selected = field === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => {
                    setField(f.id);
                    setErrors((p) => ({ ...p, field: undefined }));
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all"
                  style={{
                    borderRadius: "9999px",
                    border: selected
                      ? "1px solid var(--color-neon-cyan)"
                      : "1px solid rgba(90,45,160,0.3)",
                    background: selected
                      ? "rgba(0,212,255,0.1)"
                      : "rgba(13,11,24,0.5)",
                    color: selected
                      ? "var(--color-neon-cyan)"
                      : "var(--color-text-secondary)",
                  }}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  {f.label}
                </button>
              );
            })}
          </div>
          {errors.field && (
            <p
              className="mt-2 text-[11px] font-mono"
              style={{ color: "var(--color-neon-pink)" }}
            >
              {errors.field}
            </p>
          )}
        </div>

        {/* Sub-fields */}
        <div>
          <SectionHeader label="[03] Focus Areas" />
          <TagInput
            tags={subFields}
            onChange={setSubFields}
            placeholder={
              SUB_FIELD_PLACEHOLDER[field] ??
              "e.g. specific topics… press Enter"
            }
          />
          {errors.subFields && (
            <p
              className="mt-2 text-[11px] font-mono"
              style={{ color: "var(--color-neon-pink)" }}
            >
              {errors.subFields}
            </p>
          )}
        </div>

        {/* Preferred Formats */}
        <div>
          <SectionHeader label="[04] Content Formats (optional)" />
          <div className="grid grid-cols-2 gap-2">
            {FORMAT_CARDS.map((card) => {
              const Icon = card.icon;
              const selected = preferredFormats.includes(card.id);
              return (
                <button
                  key={card.id}
                  type="button"
                  onClick={() =>
                    setPreferredFormats((prev) =>
                      prev.includes(card.id)
                        ? prev.filter((f) => f !== card.id)
                        : [...prev, card.id],
                    )
                  }
                  className="relative flex items-center gap-3 p-3 text-left transition-all"
                  style={{
                    borderRadius: "0.75rem",
                    border: selected
                      ? "1px solid rgba(0,212,255,0.4)"
                      : "1px solid rgba(90,45,160,0.25)",
                    background: selected
                      ? "rgba(0,212,255,0.06)"
                      : "rgba(13,11,24,0.5)",
                  }}
                >
                  {selected && (
                    <div
                      className="absolute top-2 right-2 w-4 h-4 rounded-full flex items-center justify-center"
                      style={{ background: "var(--color-neon-cyan)" }}
                    >
                      <Check
                        className="w-2.5 h-2.5"
                        style={{ color: "var(--color-space-black)" }}
                        strokeWidth={3}
                      />
                    </div>
                  )}
                  <Icon
                    className="w-4 h-4 shrink-0"
                    style={{
                      color: selected
                        ? "var(--color-neon-cyan)"
                        : "var(--color-text-secondary)",
                    }}
                  />
                  <div>
                    <p
                      className="text-xs font-semibold"
                      style={{
                        color: selected
                          ? "var(--color-neon-cyan)"
                          : "var(--color-text-primary)",
                      }}
                    >
                      {card.label}
                    </p>
                    <p
                      className="text-[10px] mt-0.5"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      {card.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Refresh Interval */}
        <div>
          <SectionHeader label="[05] Refresh Cadence" />
          <div className="flex gap-2">
            {[3, 6].map((hrs) => (
              <button
                key={hrs}
                type="button"
                onClick={() => setRefreshInterval(hrs)}
                className="flex-1 py-2.5 text-sm font-mono font-bold uppercase tracking-widest transition-all"
                style={{
                  borderRadius: "0.5rem",
                  border:
                    refreshInterval === hrs
                      ? "1px solid var(--color-deep-purple)"
                      : "1px solid rgba(90,45,160,0.25)",
                  background:
                    refreshInterval === hrs
                      ? "rgba(90,45,160,0.2)"
                      : "rgba(13,11,24,0.5)",
                  color:
                    refreshInterval === hrs
                      ? "var(--color-text-primary)"
                      : "var(--color-text-secondary)",
                }}
              >
                Every {hrs}h
              </button>
            ))}
          </div>
          <p
            className="mt-2 text-[10px] font-mono uppercase tracking-widest"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {refreshInterval === 3
              ? "High frequency — ideal for fast-moving fields"
              : "Standard — balanced freshness and efficiency"}
          </p>
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-3 pt-4"
          style={{ borderTop: "1px solid rgba(90,45,160,0.2)" }}
        >
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-2.5 text-sm font-display font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all"
            style={{
              borderRadius: "0.5rem",
              background: loading
                ? "rgba(90,45,160,0.3)"
                : "var(--color-deep-purple)",
              color: "var(--color-text-primary)",
              opacity: loading ? 0.6 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 rounded-full border-2 border-t-transparent"
                  style={{
                    borderColor: "rgba(240,238,255,0.4)",
                    borderTopColor: "transparent",
                  }}
                />
                Saving…
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-all"
            style={{
              borderRadius: "0.5rem",
              border: "1px solid rgba(255,45,122,0.25)",
              background: "rgba(255,45,122,0.06)",
              color: "var(--color-text-secondary)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--color-neon-pink)";
              e.currentTarget.style.borderColor = "rgba(255,45,122,0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--color-text-secondary)";
              e.currentTarget.style.borderColor = "rgba(255,45,122,0.25)";
            }}
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </form>
    </div>
  );
}
