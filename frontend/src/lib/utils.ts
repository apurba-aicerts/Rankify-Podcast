export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function buildInputFile(content: string, episodeTitle: string, file?: File | null): File {
  if (file) return file
  let text = content.trim()
  if (episodeTitle.trim()) {
    text = `Episode title: ${episodeTitle.trim()}\n\n${text}`
  }
  return new File([text], 'input.txt', { type: 'text/plain' })
}

export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

/** Soft duration estimate from dialogue (~140 wpm). Informational only — not a promise. */
export function estimateScriptMinutes(
  dialogue: { text: string }[] | null | undefined,
): number | null {
  if (!dialogue?.length) return null
  const words = dialogue.reduce((sum, turn) => {
    const parts = turn.text.trim().split(/\s+/).filter(Boolean)
    return sum + parts.length
  }, 0)
  if (words === 0) return null
  return Math.max(1, Math.round(words / 140))
}

export function formatEstimatedDuration(minutes: number | null): string | null {
  if (minutes == null) return null
  return `~${minutes} min estimated`
}
