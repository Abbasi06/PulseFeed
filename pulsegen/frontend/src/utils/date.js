export function formatDistanceToNow(date) {
  if (!date || isNaN(date.getTime())) return '—'

  const now = new Date()
  const diff = now - date

  if (diff < 0) {
    if (diff > -300000) return 'just now'
    return 'in the future'
  }

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return `${seconds}s ago`
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days <= 30) return `${days}d ago`
  return date.toLocaleDateString()
}

export function formatTimestamp(date) {
  if (!date || isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date)
}
