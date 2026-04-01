import { motion } from "framer-motion";

const TOPIC_COLORS = {
  AI: "bg-deep-purple/80 text-white",
  Technology: "bg-neon-cyan/80 text-space-black",
  Science: "bg-neon-pink/80 text-white",
  Business: "bg-space-black/80 text-neon-cyan border border-neon-cyan/30",
  Health: "bg-deep-purple/60 text-white",
  Security: "bg-neon-pink/60 text-white",
  General: "bg-space-black/80 text-text-secondary border border-deep-purple/30",
};

function topicClass(topic) {
  return TOPIC_COLORS[topic] ?? TOPIC_COLORS.General;
}

function sourceBadge(source) {
  const s = (source || "").toLowerCase();
  if (s.includes("arxiv"))
    return { label: "ArXiv", cls: "bg-deep-purple/90 text-white border border-deep-purple/50" };
  if (s.includes("github"))
    return { label: "GitHub", cls: "bg-space-black/80 text-text-primary border border-deep-purple/30" };
  if (s.includes("youtube"))
    return { label: "YT", cls: "bg-neon-pink/90 text-white border border-neon-pink/50" };
  if (s.includes("medium") || s.includes("dev.to"))
    return { label: source, cls: "bg-neon-cyan/90 text-space-black" };
  if (s.includes("ycombinator") || s.includes("hacker news"))
    return { label: "HN", cls: "bg-deep-purple/50 text-white border border-deep-purple/40" };
  return null;
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function imgSeed(str) {
  let h = 5381;
  for (let i = 0; i < (str || "").length; i++)
    h = ((h << 5) + h) ^ str.charCodeAt(i);
  return Math.abs(h) % 1000;
}

const cardVariants = {
  hidden: { opacity: 0, filter: "blur(8px)", y: 14 },
  visible: {
    opacity: 1,
    filter: "blur(0px)",
    y: 0,
    transition: { duration: 0.42, ease: [0.21, 0.47, 0.32, 0.98] },
  },
};

export default function NewsCard({
  title,
  summary,
  source,
  url,
  topic,
  published_date,
  image_url,
  liked,
  disliked,
  saved,
  read_count,
  onLike,
  onDislike,
  onSave,
  onReadClick,
}) {
  const safeUrl = url && url !== "#" ? url : null;
  const seed = imgSeed(title);
  const imgSrc = image_url || `https://picsum.photos/seed/${seed}/800/420`;
  const badge = sourceBadge(source);

  return (
    <motion.article
      variants={cardVariants}
      className="group liquid-glass flex flex-col transition-all duration-300 hover:-translate-y-0.5"
    >
      {/* Image */}
      <div className="relative aspect-[16/9] overflow-hidden bg-space-black border-b border-deep-purple/30 shrink-0">
        <img
          src={imgSrc}
          alt=""
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          onError={(e) => {
            e.currentTarget.src = `https://picsum.photos/seed/${seed + 7}/800/420`;
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />

        {/* Topic badge */}
        <span
          className={`absolute bottom-3 left-3 px-2.5 py-1 text-xs font-semibold rounded-full backdrop-blur-sm ${topicClass(topic)}`}
        >
          {topic || "General"}
        </span>

        {/* Read count */}
        {read_count > 0 && (
          <span className="absolute bottom-3 right-3 flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-black/50 border border-deep-purple/30 text-text-secondary backdrop-blur-sm">
            <svg
              className="w-2.5 h-2.5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              />
            </svg>
            {read_count}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2.5 p-4 flex-1">
        {safeUrl ? (
          <a
            href={safeUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={onReadClick}
            className="text-sm font-bold text-text-primary leading-snug hover:text-neon-cyan transition-colors line-clamp-2"
          >
            {title}
          </a>
        ) : (
          <p className="text-sm font-bold text-text-primary leading-snug line-clamp-2">
            {title}
          </p>
        )}

        {summary && (
          <p className="text-xs text-text-secondary leading-relaxed line-clamp-3 flex-1">
            {summary}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-1.5 pt-1">
          {/* Like */}
          <ActionBtn
            active={liked}
            onClick={onLike}
            activeClass="bg-neon-pink/20 border-neon-pink/40 text-neon-pink shadow-[0_0_8px_var(--color-neon-pink)]"
            inactiveClass="bg-space-black/80 border-deep-purple/30 text-text-secondary hover:text-text-primary hover:border-deep-purple/60 hover:bg-deep-purple/10"
            aria-label={liked ? "Unlike" : "Like"}
          >
            <svg
              className="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              fill={liked ? "currentColor" : "none"}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
              />
            </svg>
          </ActionBtn>

          {/* Dislike */}
          <ActionBtn
            active={disliked}
            onClick={onDislike}
            activeClass="bg-neon-cyan/20 border-neon-cyan/40 text-neon-cyan shadow-[0_0_8px_var(--color-neon-cyan)]"
            inactiveClass="bg-space-black/80 border-deep-purple/30 text-text-secondary hover:text-text-primary hover:border-deep-purple/60 hover:bg-deep-purple/10"
            aria-label={disliked ? "Remove dislike" : "Dislike"}
          >
            <svg
              className="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              fill={disliked ? "currentColor" : "none"}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5"
              />
            </svg>
          </ActionBtn>

          {/* Save */}
          <ActionBtn
            active={saved}
            onClick={onSave}
            activeClass="bg-deep-purple/40 border-deep-purple text-text-primary shadow-[0_0_8px_var(--color-deep-purple)]"
            inactiveClass="bg-space-black/80 border-deep-purple/30 text-text-secondary hover:text-text-primary hover:border-deep-purple/60 hover:bg-deep-purple/10"
            aria-label={saved ? "Unsave" : "Save"}
          >
            <svg
              className="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              fill={saved ? "currentColor" : "none"}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17 3H7a2 2 0 00-2 2v16l7-3 7 3V5a2 2 0 00-2-2z"
              />
            </svg>
          </ActionBtn>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 pt-0.5">
          <div className="flex items-center gap-1.5 min-w-0">
            {badge && (
              <span
                className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${badge.cls} shrink-0`}
              >
                {badge.label}
              </span>
            )}
            {source && source !== "Unknown" && (
              <span className="text-xs text-text-secondary/80 truncate">{source}</span>
            )}
          </div>
          <span className="text-[10px] text-text-secondary/60 uppercase tracking-wide shrink-0">
            {formatDate(published_date)}
          </span>
        </div>
      </div>
    </motion.article>
  );
}

function ActionBtn({
  active,
  onClick,
  activeClass,
  inactiveClass,
  children,
  ...rest
}) {
  return (
    <motion.button
      onClick={onClick}
      whileTap={{ scale: 1.25 }}
      transition={{ type: "spring", stiffness: 500, damping: 22 }}
      className={`flex items-center justify-center w-7 h-7 rounded-lg border transition-all duration-200 ${active ? activeClass : inactiveClass}`}
      {...rest}
    >
      {children}
    </motion.button>
  );
}
