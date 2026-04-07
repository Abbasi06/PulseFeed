/**
 * PulseFeed Logo — "Six Signals"
 *
 * Six math marks in a tight row, each representing a dimension of
 * the knowledge feed: Σ sum · ∫ flow · ∇ gradient · φ ratio · Δ change · Ω complete.
 *
 * Props
 *  size     — mark height in px (wordmark scales proportionally)
 *  variant  — "full" | "icon" | "word"
 *  color    — "dark" | "light"
 */

const INK = "#231F20";
const CLAY = "#D97757";
const NAU = "#26498D";
const PAPER = "#FDFCF8";

interface LogoProps {
  size?: number;
  variant?: "full" | "icon" | "word";
  color?: "dark" | "light";
  className?: string;
}

// ── Σ Sigma ────────────────────────────────────────────────────────────────
function MarkSigma({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <polyline
        points="30,6 10,6 22,20 10,34 30,34"
        stroke={ink}
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="22" cy="20" r="3" fill={clay} />
    </svg>
  );
}

// ── ∫ Integral ─────────────────────────────────────────────────────────────
function MarkIntegral({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={14}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M 23,5 C 29,5 31,9 27,15 C 23,21 17,19 13,25 C 9,31 11,37 17,37"
        stroke={ink}
        strokeWidth="2.8"
        strokeLinecap="round"
        fill="none"
      />
      <line
        x1="19"
        y1="5"
        x2="27"
        y2="5"
        stroke={ink}
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <line
        x1="13"
        y1="37"
        x2="21"
        y2="37"
        stroke={ink}
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="20" cy="21" r="2.4" fill={clay} />
    </svg>
  );
}

// ── ∇ Nabla ────────────────────────────────────────────────────────────────
function MarkNabla({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <polygon
        points="20,34 4,7 36,7"
        stroke={ink}
        strokeWidth="2.5"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="20" cy="34" r="3" fill={clay} />
      <circle cx="20" cy="34" r="5.5" fill={clay} opacity="0.18" />
    </svg>
  );
}

// ── φ Phi ──────────────────────────────────────────────────────────────────
function MarkPhi({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="20" cy="20" r="13" stroke={ink} strokeWidth="2.3" />
      <line
        x1="20"
        y1="5"
        x2="20"
        y2="35"
        stroke={ink}
        strokeWidth="2.3"
        strokeLinecap="round"
      />
      <line
        x1="7"
        y1="20"
        x2="33"
        y2="20"
        stroke={clay}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeDasharray="3 2.5"
      />
    </svg>
  );
}

// ── Δ Delta ────────────────────────────────────────────────────────────────
function MarkDelta({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <polygon
        points="20,5 37,35 3,35"
        stroke={ink}
        strokeWidth="2.5"
        strokeLinejoin="round"
        fill="none"
      />
      <polyline
        points="10,28 15,28 17,22 20,32 22,24 25,28 30,28"
        stroke={clay}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

// ── Ω Omega ────────────────────────────────────────────────────────────────
function MarkOmega({ ink, clay }: { ink: string; clay: string }) {
  return (
    <svg
      width={18}
      height={18}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M 7,34 C 7,34 10,34 12,34 C 10,30 8,26 8,20 C 8,11 13,5 20,5 C 27,5 32,11 32,20 C 32,26 30,30 28,34 C 30,34 33,34 33,34"
        stroke={ink}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="20" cy="5" r="2.8" fill={clay} />
    </svg>
  );
}

// (other marks kept for reference but not rendered)

export default function Logo({
  size = 36,
  variant = "full",
  color = "dark",
  className = "",
}: LogoProps) {
  const isDark = color === "dark";
  const ink = isDark ? INK : PAPER;
  const textColor = isDark ? INK : PAPER;

  // Match icon size to text cap-height
  const fontSize = size * 0.42;
  const iconSize = fontSize * 1.1; // slightly taller than cap-height so Σ optically aligns

  const sigmaIcon = (
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      style={{ display: "block", flexShrink: 0 }}
    >
      <polyline
        points="30,6 10,6 22,20 10,34 30,34"
        stroke={ink}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );

  const wordmark = (
    <div style={{ userSelect: "none", lineHeight: 1 }}>
      <span
        style={{
          fontFamily: "var(--font-display, Georgia, serif)",
          fontWeight: 700,
          fontSize,
          letterSpacing: "-0.04em",
          textTransform: "uppercase" as const,
          color: textColor,
        }}
      >
        Pulse
      </span>
      <span
        style={{
          fontFamily: "var(--font-display, Georgia, serif)",
          fontWeight: 700,
          fontSize,
          letterSpacing: "-0.04em",
          textTransform: "uppercase" as const,
          color: CLAY,
          marginLeft: fontSize * 0.2,
        }}
      >
        Feed
      </span>
    </div>
  );

  if (variant === "icon") {
    return <div className={className}>{sigmaIcon}</div>;
  }

  if (variant === "word") {
    return <div className={className}>{wordmark}</div>;
  }

  return (
    <div
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: fontSize * 0.5,
      }}
    >
      {sigmaIcon}
      {wordmark}
    </div>
  );
}
