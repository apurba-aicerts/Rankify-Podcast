import { Pause, Play } from 'lucide-react'
import { cn } from '../lib/utils'

interface VoicePlayButtonProps {
  voiceId: string
  isPlaying: boolean
  onToggle: (voiceId: string) => void
  className?: string
}

export function VoicePlayButton({
  voiceId,
  isPlaying,
  onToggle,
  className,
}: VoicePlayButtonProps) {
  return (
    <button
      type="button"
      onClick={() => onToggle(voiceId)}
      className={cn(
        'rounded-lg p-2 transition-colors',
        isPlaying
          ? 'bg-brand-light text-brand'
          : 'text-gray-500 hover:bg-gray-100 hover:text-brand',
        className,
      )}
      title={isPlaying ? 'Pause voice sample' : 'Play voice sample'}
      aria-label={isPlaying ? 'Pause voice sample' : 'Play voice sample'}
    >
      {isPlaying ? (
        <Pause className="h-4 w-4 fill-current" />
      ) : (
        <Play className="h-4 w-4 fill-current" />
      )}
    </button>
  )
}
