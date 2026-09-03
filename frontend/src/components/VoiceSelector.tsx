import { Trash2 } from 'lucide-react'
import type { VoiceInfo } from '../types/api'
import { cn } from '../lib/utils'
import { VoicePlayButton } from './VoicePlayButton'
import { useVoiceSamplePlayer } from '../hooks/useVoiceSamplePlayer'

const ACCENT_COLORS = ['border-l-brand', 'border-l-blue-400', 'border-l-emerald-400', 'border-l-violet-400']

export interface SpeakerConfig {
  label: string
  voiceId: string
}

interface VoiceSelectorProps {
  speakers: SpeakerConfig[]
  voices: VoiceInfo[]
  onChange: (speakers: SpeakerConfig[]) => void
  minSpeakers?: number
  maxSpeakers?: number
}

export function VoiceSelector({
  speakers,
  voices,
  onChange,
  minSpeakers = 1,
  maxSpeakers = 2,
}: VoiceSelectorProps) {
  const { toggle, isVoicePlaying } = useVoiceSamplePlayer(voices)

  const updateSpeaker = (index: number, patch: Partial<SpeakerConfig>) => {
    onChange(speakers.map((s, i) => (i === index ? { ...s, ...patch } : s)))
  }

  const addSpeaker = () => {
    if (speakers.length >= maxSpeakers) return
    const defaultVoice = voices[0]?.id ?? 'achernar'
    onChange([
      ...speakers,
      { label: `Speaker ${speakers.length + 1}`, voiceId: defaultVoice },
    ])
  }

  const removeSpeaker = (index: number) => {
    if (speakers.length <= minSpeakers) return
    onChange(speakers.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3">
      {speakers.map((speaker, index) => (
        <div
          key={index}
          className={cn(
            'rounded-xl border border-gray-100 bg-gray-50/80 p-4 border-l-4',
            ACCENT_COLORS[index % ACCENT_COLORS.length],
          )}
        >
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={speaker.label}
              onChange={(e) => updateSpeaker(index, { label: e.target.value })}
              className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium"
              placeholder={`Speaker ${index + 1}`}
            />
            <VoicePlayButton
              voiceId={speaker.voiceId}
              isPlaying={isVoicePlaying(speaker.voiceId)}
              onToggle={toggle}
              className="hover:bg-white"
            />
            {speakers.length > minSpeakers && (
              <button
                type="button"
                onClick={() => removeSpeaker(index)}
                className="rounded-lg p-2 text-gray-400 hover:bg-white hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
          <select
            value={speaker.voiceId}
            onChange={(e) => updateSpeaker(index, { voiceId: e.target.value })}
            className="mt-3 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} — {v.description}
              </option>
            ))}
          </select>
        </div>
      ))}
      {speakers.length < maxSpeakers && (
        <button
          type="button"
          onClick={addSpeaker}
          className="text-sm font-medium text-brand hover:text-brand-dark"
        >
          + Add speaker
        </button>
      )}
    </div>
  )
}
