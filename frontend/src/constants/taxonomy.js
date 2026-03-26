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
    description: "Systems · Distributed · Infrastructure",
    color: "violet",
    subFields: [
      "Distributed Systems",
      "KEDA & Autoscaling",
      "System Design (L7)",
      "Rust/Go Systems",
      "Cloud Native Infrastructure",
      "API Architecture",
      "Platform Engineering",
      "High Performance Computing",
    ],
  },
  {
    id: "ai-engineering",
    label: "Gen AI Engineering",
    shortLabel: "AI",
    backendField: "AI & Machine Learning",
    description: "Inference · Agents · RAG",
    color: "aurora-pink",
    subFields: [
      "Agentic Workflows",
      "vLLM & Inference",
      "Inference Cascades",
      "Vector Databases",
      "Contextual Bandits",
      "RAG Systems",
      "Fine-tuning (LoRA/QLoRA)",
      "MLOps & LLMOps",
    ],
  },
  {
    id: "cybersecurity",
    label: "Cybersecurity",
    shortLabel: "Cyber",
    backendField: "Cybersecurity",
    description: "Offensive · Defensive · Cloud",
    color: "steel-blue",
    subFields: [
      "Zero Trust Architecture",
      "Cloud Security Posture",
      "AppSec & DevSecOps",
      "AI Security (OWASP LLM)",
      "Threat Intelligence",
      "Identity & Access",
      "OSINT & Evasion",
      "Security Engineering",
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
  "aurora-pink": {
    card: "border-aurora-pink ring-2 ring-aurora-pink/25 bg-aurora-pink/5",
    cardIcon: "text-aurora-pink",
    cardLabel: "text-aurora-pink",
    chip: "border-aurora-pink bg-aurora-pink/10 text-aurora-pink ring-1 ring-aurora-pink/20",
    chipCheck: "bg-aurora-pink",
    progress: "bg-aurora-pink",
  },
  "steel-blue": {
    card: "border-steel-blue ring-2 ring-steel-blue/25 bg-steel-blue/5",
    cardIcon: "text-steel-blue",
    cardLabel: "text-steel-blue",
    chip: "border-steel-blue bg-steel-blue/10 text-steel-blue ring-1 ring-steel-blue/20",
    chipCheck: "bg-steel-blue",
    progress: "bg-steel-blue",
  },
};
