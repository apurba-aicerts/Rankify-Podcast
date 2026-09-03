import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Plus, Sparkles, Trash2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { generatePodcastFromScript } from '../api/scripts'
import { AppLayout } from '../components/layout/AppLayout'
import { VoicePlayButton } from '../components/VoicePlayButton'
import { Button } from '../components/ui/Button'
import { LoadingOverlay } from '../components/ui/Shared'
import { useTtsModels, useVoices } from '../hooks/useCatalog'
import { useScript } from '../hooks/useScripts'
import { useVoiceSamplePlayer } from '../hooks/useVoiceSamplePlayer'
import { applyOptimisticPodcastGeneration } from '../lib/projectItems'
import type { DialogueTurn, PodcastScript } from '../types/api'

export function ScriptReviewPage() {
  const { projectId = '', scriptId = '' } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: stored, isLoading, error: loadError } = useScript(projectId, scriptId)
  const { data: voicesData } = useVoices()
  const { data: ttsModelsData } = useTtsModels()
  const voices = voicesData?.voices ?? []
  const ttsModels = ttsModelsData?.models ?? []

  const [script, setScript] = useState<PodcastScript | null>(null)
  const [ttsModel, setTtsModel] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { toggle, isVoicePlaying } = useVoiceSamplePlayer(voices)

  useEffect(() => {
    if (stored?.status === 'generating' || stored?.status === 'published') {
      navigate(`/projects/${projectId}`, { replace: true })
    }
  }, [stored, projectId, navigate])

  useEffect(() => {
    if (!stored || stored.status === 'generating') return
    if (stored.status === 'failed') {
      setError(stored.error_message ?? 'Script generation failed.')
      return
    }
    if (stored.status === 'published') return
    if (stored.script) {
      setScript(stored.script)
      setTtsModel(stored.tts_model)
    }
  }, [stored])

  useEffect(() => {
    if (ttsModels.length && !ttsModel) setTtsModel(ttsModels[0].id)
  }, [ttsModels, ttsModel])

  if (isLoading) {
    return (
      <AppLayout>
        <LoadingOverlay message="Loading script…" />
      </AppLayout>
    )
  }

  if (stored?.status === 'generating' || stored?.status === 'published') {
    return (
      <AppLayout>
        <LoadingOverlay message="Opening project…" />
      </AppLayout>
    )
  }

  if (loadError || !stored || !script) {
    return (
      <AppLayout>
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {error ?? 'Script not found or not ready.'}
        </div>
        <Button className="mt-4" variant="secondary" onClick={() => navigate(`/projects/${projectId}`)}>
          Back to project
        </Button>
      </AppLayout>
    )
  }

  const updateSpeaker = (index: number, field: 'name' | 'voice_id', value: string) => {
    setScript({
      ...script,
      speakers: script.speakers.map((s, i) => (i === index ? { ...s, [field]: value } : s)),
    })
  }

  const updateTurn = (index: number, field: keyof DialogueTurn, value: string) => {
    setScript({
      ...script,
      dialogue: script.dialogue.map((t, i) => (i === index ? { ...t, [field]: value } : t)),
    })
  }

  const addTurn = () => {
    const speaker = script.speakers[0]?.name ?? 'Speaker'
    setScript({ ...script, dialogue: [...script.dialogue, { speaker, text: '' }] })
  }

  const removeTurn = (index: number) => {
    setScript({ ...script, dialogue: script.dialogue.filter((_, i) => i !== index) })
  }

  const handleGenerate = () => {
    if (script.speakers.length < 1 || script.speakers.length > 2) {
      setError('Gemini TTS supports 1–2 speakers only. Reduce speakers before generating audio.')
      return
    }
    setError(null)
    applyOptimisticPodcastGeneration(qc, projectId, scriptId, script)
    navigate(`/projects/${projectId}`, { replace: true })

    void generatePodcastFromScript(projectId, scriptId, ttsModel, script)
      .then(() => qc.invalidateQueries({ queryKey: ['projects', projectId] }))
      .catch(() => qc.invalidateQueries({ queryKey: ['projects', projectId] }))
  }

  return (
    <AppLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Review &amp; edit script</h1>
          <p className="mt-1 text-sm text-gray-500">Adjust dialogue before generating audio</p>
        </div>
        <Button variant="secondary" onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Button>
      </div>

      <div className="space-y-6 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs font-medium text-gray-500">Title</label>
            <input
              value={script.title}
              onChange={(e) => setScript({ ...script, title: e.target.value })}
              className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500">TTS model</label>
            <select
              value={ttsModel}
              onChange={(e) => setTtsModel(e.target.value)}
              className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-2 text-sm"
            >
              {ttsModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-500">Description</label>
          <textarea
            value={script.description}
            onChange={(e) => setScript({ ...script, description: e.target.value })}
            rows={2}
            className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-2 text-sm"
          />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-900">Speakers</h3>
          <p className="mt-1 text-xs text-gray-400">Gemini TTS allows 1–2 speakers</p>
          {script.speakers.length > 2 && (
            <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              This script has {script.speakers.length} speakers. Remove extras before generating
              audio.
            </p>
          )}
          <div className="mt-3 space-y-3">
            {script.speakers.map((speaker, index) => (
              <div key={index} className="flex flex-wrap items-center gap-2">
                <input
                  value={speaker.name}
                  onChange={(e) => updateSpeaker(index, 'name', e.target.value)}
                  className="min-w-[120px] flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <select
                  value={speaker.voice_id}
                  onChange={(e) => updateSpeaker(index, 'voice_id', e.target.value)}
                  className="min-w-[200px] flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                >
                  {voices.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} — {v.description}
                    </option>
                  ))}
                </select>
                <VoicePlayButton
                  voiceId={speaker.voice_id}
                  isPlaying={isVoicePlaying(speaker.voice_id)}
                  onToggle={toggle}
                />
                {script.speakers.length > 1 && (
                  <button
                    type="button"
                    onClick={() =>
                      setScript({
                        ...script,
                        speakers: script.speakers.filter((_, i) => i !== index),
                      })
                    }
                    className="rounded-lg p-2 text-gray-400 hover:text-red-500"
                    aria-label="Remove speaker"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Dialogue</h3>
            <button
              type="button"
              onClick={addTurn}
              className="flex items-center gap-1 text-sm text-brand hover:text-brand-dark"
            >
              <Plus className="h-4 w-4" />
              Add line
            </button>
          </div>
          <div className="mt-3 space-y-3">
            {script.dialogue.map((turn, index) => (
              <div key={index} className="flex gap-2 rounded-xl bg-gray-50 p-3">
                <select
                  value={turn.speaker}
                  onChange={(e) => updateTurn(index, 'speaker', e.target.value)}
                  className="w-36 shrink-0 rounded-lg border border-gray-200 bg-white px-2 py-2 text-sm"
                >
                  {script.speakers.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <textarea
                  value={turn.text}
                  onChange={(e) => updateTurn(index, 'text', e.target.value)}
                  rows={2}
                  className="min-h-[44px] flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
                />
                <button
                  type="button"
                  onClick={() => removeTurn(index)}
                  className="self-start rounded-lg p-2 text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <Button
          onClick={handleGenerate}
          disabled={script.speakers.length < 1 || script.speakers.length > 2}
        >
          <Sparkles className="h-4 w-4" />
          Generate podcast audio
        </Button>
      </div>
    </AppLayout>
  )
}

