const TOPIC_COLORS = {
  AI: 'bg-violet-500/80 text-white',
  Technology: 'bg-blue-500/80 text-white',
  Science: 'bg-cyan-500/80 text-white',
  Business: 'bg-amber-500/80 text-white',
  Health: 'bg-green-500/80 text-white',
  General: 'bg-slate-500/80 text-white',
}

function topicClass(topic) {
  return TOPIC_COLORS[topic] ?? TOPIC_COLORS.General
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

function imgSeed(str) {
  let h = 5381
  for (let i = 0; i < (str || '').length; i++) h = ((h << 5) + h) ^ str.charCodeAt(i)
  return Math.abs(h) % 1000
}

export default function NewsCard({ id, title, summary, source, url, topic, published_date, image_url, liked, onLike }) {
  const safeUrl = url && url !== '#' ? url : null
  const seed = imgSeed(title)
  const imgSrc = image_url || `https://picsum.photos/seed/${seed}/800/420`

  return (
    <article className="group bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden flex flex-col hover:border-slate-500 hover:shadow-xl hover:shadow-black/40 transition-all duration-200">
      {/* Image */}
      <div className="relative aspect-[16/9] overflow-hidden bg-slate-800 shrink-0">
        <img
          src={imgSrc}
          alt=""
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          onError={(e) => { e.currentTarget.src = `https://picsum.photos/seed/${seed + 7}/800/420` }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        {/* Topic badge */}
        <span className={`absolute bottom-3 left-3 px-2.5 py-1 text-xs font-semibold rounded-full backdrop-blur-sm ${topicClass(topic)}`}>
          {topic || 'General'}
        </span>
        {/* Heart button */}
        <button
          onClick={onLike}
          className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/40 backdrop-blur-sm hover:bg-black/70 transition-colors"
          aria-label={liked ? 'Unlike' : 'Like'}
        >
          <svg
            className={`w-4 h-4 transition-colors ${liked ? 'text-rose-500' : 'text-white'}`}
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            fill={liked ? 'currentColor' : 'none'}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
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
            className="text-sm font-bold text-slate-100 leading-snug hover:text-violet-300 transition-colors line-clamp-2"
          >
            {title}
          </a>
        ) : (
          <p className="text-sm font-bold text-slate-100 leading-snug line-clamp-2">{title}</p>
        )}

        {summary && (
          <p className="text-xs text-slate-400 leading-relaxed line-clamp-3 flex-1">{summary}</p>
        )}

        <div className="flex items-center justify-between gap-2 pt-1">
          {source && source !== 'Unknown'
            ? <span className="text-xs text-slate-500 truncate">{source}</span>
            : <span />
          }
          <span className="text-xs text-slate-600 shrink-0">{formatDate(published_date)}</span>
        </div>
      </div>
    </article>
  )
}
