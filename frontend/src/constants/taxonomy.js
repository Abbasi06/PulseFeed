/**
 * Hierarchical interest taxonomy.
 *
 * Each role maps to exactly one backend VALID_FIELD value (backendField).
 * Sub-fields are the curated chip options shown at Level 2.
 *
 * To add a new role: append a new entry to ROLES.
 * To add sub-fields: extend the subFields array for the relevant role.
 */

export const MIN_SUBFIELDS = 5;

export const ROLES = [
  {
    id: "software-engineering",
    label: "Software Engineering",
    shortLabel: "SWE",
    backendField: "Software Engineering",
    description: "Systems · Web · Infrastructure",
    color: "violet",
    subFields: [
      "Distributed Systems",
      "Cloud Native",
      "Frontend (React/Next.js)",
      "DevOps",
      "Rust/Go Systems",
      "API Design",
      "Platform Engineering",
      "Open Source",
    ],
  },
  {
    id: "ai-engineering",
    label: "AI Engineering",
    shortLabel: "AI",
    backendField: "AI & Machine Learning",
    description: "Models · Pipelines · Agents",
    color: "emerald",
    subFields: [
      "LLM Orchestration",
      "Computer Vision",
      "Agentic Workflows",
      "AI Safety",
      "Fine-tuning",
      "RAG Systems",
      "Multimodal Models",
      "MLOps",
    ],
  },
  {
    id: "cybersecurity",
    label: "Cybersecurity",
    shortLabel: "Cyber",
    backendField: "Cybersecurity",
    description: "Offensive · Defensive · Cloud",
    color: "rose",
    subFields: [
      "Zero Trust Architecture",
      "Pentesting",
      "Cloud Security",
      "Threat Hunting",
      "AppSec",
      "Malware Analysis",
      "Identity & Access",
      "OSINT",
    ],
  },
];

/** Colour tokens per role — Tailwind classes */
export const ROLE_COLORS = {
  violet: {
    card: "border-violet-500 ring-2 ring-violet-500/25 bg-violet-500/5",
    cardIcon: "text-violet-400",
    cardLabel: "text-violet-300",
    chip: "border-violet-500 bg-violet-500/10 text-violet-300 ring-1 ring-violet-500/20",
    chipCheck: "bg-violet-500",
    progress: "bg-violet-500",
  },
  emerald: {
    card: "border-emerald-500 ring-2 ring-emerald-500/25 bg-emerald-500/5",
    cardIcon: "text-emerald-400",
    cardLabel: "text-emerald-300",
    chip: "border-emerald-500 bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/20",
    chipCheck: "bg-emerald-500",
    progress: "bg-emerald-500",
  },
  rose: {
    card: "border-rose-500 ring-2 ring-rose-500/25 bg-rose-500/5",
    cardIcon: "text-rose-400",
    cardLabel: "text-rose-300",
    chip: "border-rose-500 bg-rose-500/10 text-rose-300 ring-1 ring-rose-500/20",
    chipCheck: "bg-rose-500",
    progress: "bg-rose-500",
  },
};
