/**
 * Hierarchical interest taxonomy.
 */

export const MIN_SUBFIELDS = 5;

export const ROLES = [
  {
    id: "software-engineering",
    label: "Software Engineering",
    shortLabel: "SWE",
    backendField: "Software Engineering",
    description: "Systems · Distributed · Infrastructure",
    color: "ink",
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
    color: "ink",
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
    color: "ink",
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

/** Colour tokens per role adapted for Vintage Editorial */
export const ROLE_COLORS = {
  ink: {
    card: "border-[3px] border-ink bg-paper",
    cardIcon: "text-clay",
    cardLabel: "text-ink font-bold",
    chip: "border-ink border-2 bg-clay text-paper",
    chipCheck: "bg-paper text-clay",
    progress: "bg-clay",
  },
};
