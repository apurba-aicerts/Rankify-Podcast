import { useEffect, useRef, useState } from 'react'
import type { VoiceInfo } from '../types/api'

export function useVoiceSamplePlayer(voices: VoiceInfo[]) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [activeVoiceId, setActiveVoiceId] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    return () => {
      audioRef.current?.pause()
    }
  }, [])

  const toggle = (voiceId: string) => {
    const voice = voices.find((v) => v.id === voiceId)
    if (!voice?.audio_url) return

    if (activeVoiceId === voiceId && audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        void audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false))
      }
      return
    }

    if (audioRef.current) {
      audioRef.current.pause()
    }

    const audio = new Audio(voice.audio_url)
    audioRef.current = audio
    setActiveVoiceId(voiceId)
    setIsPlaying(true)

    audio.onended = () => {
      setIsPlaying(false)
      setActiveVoiceId(null)
    }

    void audio.play().catch(() => {
      setIsPlaying(false)
      setActiveVoiceId(null)
    })
  }

  const isVoicePlaying = (voiceId: string) => activeVoiceId === voiceId && isPlaying

  return { toggle, isVoicePlaying }
}
