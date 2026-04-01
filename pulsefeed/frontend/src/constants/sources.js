/**
 * Source taxonomy for the Source & Creator picker.
 *
 * To add a new category: append to SOURCE_CATEGORIES.
 * To add role-specific suggestions: extend ROLE_SUGGESTED_SOURCES / ROLE_SUGGESTED_CREATORS.
 */

export const SOURCE_CATEGORIES = [
  {
    id: "video",
    label: "Video",
    lucideIcon: "Youtube",
    description: "Channels & tutorials",
    sources: [
      {
        id: "youtube",
        label: "YouTube",
        description: "Creators & in-depth tutorials",
        lucideIcon: "Youtube",
      },
    ],
  },
  {
    id: "deep-dive",
    label: "Deep Dive",
    lucideIcon: "FileSearch",
    description: "Research & papers",
    sources: [
      {
        id: "arxiv",
        label: "ArXiv",
        description: "Preprints & cutting-edge research",
        lucideIcon: "FlaskConical",
      },
      {
        id: "semantic-scholar",
        label: "Semantic Scholar",
        description: "AI-powered paper discovery",
        lucideIcon: "Search",
      },
      {
        id: "papers-with-code",
        label: "Papers with Code",
        description: "ML papers + implementations",
        lucideIcon: "Code2",
      },
    ],
  },
  {
    id: "industry-blogs",
    label: "Industry Blogs",
    lucideIcon: "Newspaper",
    description: "Articles & newsletters",
    sources: [
      {
        id: "medium",
        label: "Medium",
        description: "Dev articles & opinion pieces",
        lucideIcon: "FileText",
      },
      {
        id: "substack",
        label: "Substack",
        description: "Expert newsletters",
        lucideIcon: "Mail",
      },
      {
        id: "hashnode",
        label: "Hashnode",
        description: "Dev community blogs",
        lucideIcon: "Hash",
      },
      {
        id: "engineering-blogs",
        label: "Engineering Blogs",
        description: "Netflix · Uber · Meta · Stripe",
        lucideIcon: "Building2",
      },
    ],
  },
  {
    id: "social-code",
    label: "Social & Code",
    lucideIcon: "Github",
    description: "Repos, forums & feeds",
    sources: [
      {
        id: "github-trending",
        label: "GitHub Trending",
        description: "Top repositories this week",
        lucideIcon: "TrendingUp",
      },
      {
        id: "hacker-news",
        label: "Hacker News",
        description: "Show HN · top links",
        lucideIcon: "Flame",
      },
      {
        id: "reddit",
        label: "Reddit",
        description: "r/programming · r/MachineLearning · r/netsec",
        lucideIcon: "MessageSquare",
      },
      {
        id: "x-tech",
        label: "X — Tech Lists",
        description: "Curated tech & AI lists",
        lucideIcon: "Twitter",
      },
    ],
  },
  {
    id: "ai-first",
    label: "AI-First",
    lucideIcon: "Sparkles",
    description: "AI-curated digests",
    sources: [
      {
        id: "ai-summaries",
        label: "AI Digest",
        description: "Gemini-curated whitepaper summaries",
        lucideIcon: "Sparkles",
      },
      {
        id: "hugging-face",
        label: "Hugging Face",
        description: "Model releases & datasets",
        lucideIcon: "Bot",
      },
    ],
  },
];

/** Source IDs to pre-highlight based on the user's chosen backend field. */
export const ROLE_SUGGESTED_SOURCES = {
  "Software Engineering": [
    "github-trending",
    "engineering-blogs",
    "hacker-news",
    "youtube",
    "medium",
  ],
  "AI & Machine Learning": [
    "arxiv",
    "papers-with-code",
    "hugging-face",
    "ai-summaries",
    "youtube",
  ],
  Cybersecurity: [
    "hacker-news",
    "reddit",
    "medium",
    "substack",
    "github-trending",
  ],
};

/** Creator/voice suggestions shown as quick-add chips per role. */
export const ROLE_SUGGESTED_CREATORS = {
  "Software Engineering": [
    "Fireship",
    "Theo (t3.gg)",
    "The Primeagen",
    "TechWorld with Nana",
    "Hussein Nasser",
  ],
  "AI & Machine Learning": [
    "Andrej Karpathy",
    "Yannic Kilcher",
    "Two Minute Papers",
    "Hugging Face",
    "Sebastian Raschka",
  ],
  Cybersecurity: [
    "John Hammond",
    "LiveOverflow",
    "David Bombal",
    "TCM Security",
    "IppSec",
  ],
};
