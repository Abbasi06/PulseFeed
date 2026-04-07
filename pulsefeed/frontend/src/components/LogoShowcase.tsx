const INK = "#231F20";
const CLAY = "#D97757";
const NAU = "#26498D";

// ── A · Sigma Σ — "sum of all signals" ───────────────────────────────────────
function MarkA() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* Geometric Σ path */}
      <polyline
        points="30,6 10,6 22,20 10,34 30,34"
        stroke={INK}
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Clay dot at vertex */}
      <circle cx="22" cy="20" r="2.5" fill={CLAY} />
    </svg>
  );
}

// ── B · Integral ∫ — "continuous flow of knowledge" ─────────────────────────
function MarkB() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* S-curve integral sign */}
      <path
        d="M 23,5 C 29,5 31,9 27,15 C 23,21 17,19 13,25 C 9,31 11,37 17,37"
        stroke={INK}
        strokeWidth="2.4"
        strokeLinecap="round"
        fill="none"
      />
      {/* Top serif */}
      <line
        x1="19"
        y1="5"
        x2="27"
        y2="5"
        stroke={INK}
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Bottom serif */}
      <line
        x1="13"
        y1="37"
        x2="21"
        y2="37"
        stroke={INK}
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Clay accent — midpoint dot */}
      <circle cx="20" cy="21" r="2.2" fill={CLAY} />
    </svg>
  );
}

// ── C · Nabla ∇ — "gradient descent toward high signal" ──────────────────────
function MarkC() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* Inverted triangle */}
      <polygon
        points="20,34 4,7 36,7"
        stroke={INK}
        strokeWidth="2.2"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Clay dot — the target/signal at apex */}
      <circle cx="20" cy="34" r="2.8" fill={CLAY} />
      <circle cx="20" cy="34" r="5" fill={CLAY} opacity="0.15" />
      {/* Nautical inner marker */}
      <circle cx="20" cy="19" r="1.4" fill={NAU} opacity="0.5" />
    </svg>
  );
}

// ── D · Phi φ — "golden ratio / perfect signal" ───────────────────────────────
function MarkD() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* Circle */}
      <circle cx="20" cy="20" r="14" stroke={INK} strokeWidth="2.0" />
      {/* Vertical bar through circle */}
      <line
        x1="20"
        y1="4"
        x2="20"
        y2="36"
        stroke={INK}
        strokeWidth="2.0"
        strokeLinecap="round"
      />
      {/* Horizontal midline — creates the φ feel */}
      <line
        x1="6"
        y1="20"
        x2="34"
        y2="20"
        stroke={CLAY}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="3 2"
      />
    </svg>
  );
}

// ── E · Delta Δ — "rate of change / always current" ──────────────────────────
function MarkE() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* Bold triangle */}
      <polygon
        points="20,5 37,35 3,35"
        stroke={INK}
        strokeWidth="2.2"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Clay pulse line inside — a mini ECG inside the triangle */}
      <polyline
        points="10,28 15,28 17,22 20,32 22,24 25,28 30,28"
        stroke={CLAY}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

// ── F · Omega Ω — "the complete signal / final intelligence" ─────────────────
function MarkF() {
  return (
    <svg width={32} height={32} viewBox="0 0 40 40" fill="none">
      {/* Omega shape: arc + two feet */}
      <path
        d="M 7,34 C 7,34 10,34 12,34 C 10,30 8,26 8,20 C 8,11 13,5 20,5 C 27,5 32,11 32,20 C 32,26 30,30 28,34 C 30,34 33,34 33,34"
        stroke={INK}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Clay dot at crown */}
      <circle cx="20" cy="5" r="2.5" fill={CLAY} />
    </svg>
  );
}

const MARKS = [
  {
    id: "A",
    sym: "Σ",
    label: "Sigma",
    Mark: MarkA,
    desc: "Sum of all signals",
  },
  {
    id: "B",
    sym: "∫",
    label: "Integral",
    Mark: MarkB,
    desc: "Continuous knowledge flow",
  },
  {
    id: "C",
    sym: "∇",
    label: "Nabla",
    Mark: MarkC,
    desc: "Gradient toward high signal",
  },
  {
    id: "D",
    sym: "φ",
    label: "Phi",
    Mark: MarkD,
    desc: "Golden ratio / perfection",
  },
  { id: "E", sym: "Δ", label: "Delta", Mark: MarkE, desc: "Rate of change" },
  {
    id: "F",
    sym: "Ω",
    label: "Omega",
    Mark: MarkF,
    desc: "Complete intelligence",
  },
];

export default function LogoShowcase() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      {MARKS.map(({ id, label, Mark, desc }) => (
        <div
          key={id}
          title={`${label} — ${desc}`}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 3,
            padding: "4px 6px",
            border: `1px solid ${INK}`,
            cursor: "pointer",
          }}
        >
          <Mark />
          <span
            style={{
              fontSize: 8,
              fontFamily: "monospace",
              color: INK,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            {id}
          </span>
        </div>
      ))}
    </div>
  );
}
