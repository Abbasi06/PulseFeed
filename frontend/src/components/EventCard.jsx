import { motion } from "framer-motion";

const cardVariants = {
  hidden: { opacity: 0, filter: "blur(8px)", y: 12 },
  visible: {
    opacity: 1,
    filter: "blur(0px)",
    y: 0,
    transition: { duration: 0.45, ease: [0.21, 0.47, 0.32, 0.98] },
  },
};

const TYPE_COLORS = {
  Conference: "bg-blue-500/80 text-white",
  Meetup: "bg-green-500/80 text-white",
  Workshop: "bg-amber-500/80 text-white",
  Webinar: "bg-cyan-500/80 text-white",
  Summit: "bg-rose-500/80 text-white",
};

function typeClass(type) {
  return TYPE_COLORS[type] ?? "bg-slate-500/80 text-white";
}

function imgSeed(str) {
  let h = 5381;
  for (let i = 0; i < (str || "").length; i++)
    h = ((h << 5) + h) ^ str.charCodeAt(i);
  return (Math.abs(h) % 1000) + 200;
}

export default function EventCard({
  name,
  date,
  location,
  type,
  url,
  reason,
  image_url,
  liked,
  onLike,
}) {
  const safeUrl = url && url !== "#" ? url : null;
  const displayLocation = location || "Online";
  const seed = imgSeed(name);
  const imgSrc = image_url || `https://picsum.photos/seed/${seed}/800/420`;

  return (
    <motion.article
      variants={cardVariants}
      className="group bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden flex flex-col hover:border-slate-500 hover:shadow-xl hover:shadow-black/40 transition-colors duration-200"
    >
      {/* Image */}
      <div className="relative aspect-[16/9] overflow-hidden bg-slate-800 shrink-0">
        <img
          src={imgSrc}
          alt=""
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          onError={(e) => {
            e.currentTarget.src = `https://picsum.photos/seed/${seed + 7}/800/420`;
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        {/* Type badge */}
        {type && (
          <span
            className={`absolute bottom-3 left-3 px-2.5 py-1 text-xs font-semibold rounded-full backdrop-blur-sm ${typeClass(type)}`}
          >
            {type}
          </span>
        )}
        {/* Heart button */}
        <button
          onClick={onLike}
          className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/40 backdrop-blur-sm hover:bg-black/70 transition-colors"
          aria-label={liked ? "Unlike" : "Like"}
        >
          <svg
            className={`w-4 h-4 transition-colors ${liked ? "text-rose-500" : "text-white"}`}
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
        </button>
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2.5 p-4 flex-1">
        {safeUrl ? (
          <a
            href={safeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-bold text-slate-100 leading-snug hover:text-violet-300 transition-colors"
          >
            {name}
          </a>
        ) : (
          <p className="text-sm font-bold text-slate-100 leading-snug">
            {name}
          </p>
        )}

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-1 shrink-0">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            {date}
          </div>
          <div className="flex items-center gap-1 min-w-0">
            <svg
              className="w-3.5 h-3.5 shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <span className="truncate">{displayLocation}</span>
          </div>
        </div>

        {reason && (
          <div className="bg-slate-800/80 rounded-lg px-3 py-2 border border-slate-700/50 mt-auto">
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">
              <span className="text-violet-400 font-medium">Why this · </span>
              {reason}
            </p>
          </div>
        )}
      </div>
    </motion.article>
  );
}
