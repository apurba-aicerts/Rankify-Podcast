import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Headphones, Sparkles, Wand2 } from 'lucide-react'
import { createScript } from '../api/scripts'
import { AppLayout } from '../components/layout/AppLayout'
import { FileDropzone } from '../components/FileDropzone'
import { VoiceSelector, type SpeakerConfig } from '../components/VoiceSelector'
import { Button } from '../components/ui/Button'
import { useTextModels, useTtsModels, useVoices } from '../hooks/useCatalog'
import { useProject } from '../hooks/useProjects'

export function NewPodcastPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: project } = useProject(projectId)
  const { data: voicesData } = useVoices()
  const { data: textModelsData } = useTextModels()
  const { data: ttsModelsData } = useTtsModels()

  const voices = voicesData?.voices ?? []
  const textModels = textModelsData?.models ?? []
  const ttsModels = ttsModelsData?.models ?? []

  const [episodeTitle, setEpisodeTitle] = useState('')
  const [content, setContent] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [textModel, setTextModel] = useState('')
  const [ttsModel, setTtsModel] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [speakers, setSpeakers] = useState<SpeakerConfig[]>([
    { label: 'Speaker 1', voiceId: 'achernar' },
    { label: 'Speaker 2', voiceId: 'enceladus' },
  ])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (textModels.length && !textModel) setTextModel(textModels[0].id)
  }, [textModels, textModel])

  useEffect(() => {
    if (ttsModels.length && !ttsModel) setTtsModel(ttsModels[0].id)
  }, [ttsModels, ttsModel])

  useEffect(() => {
    if (voices.length) {
      setSpeakers((prev) =>
        prev.map((s, i) => ({
          ...s,
          voiceId: s.voiceId || voices[i % voices.length]?.id || 'achernar',
        })),
      )
    }
  }, [voices])

  const validateInput = (): boolean => {
    if (!file && content.trim().length < 10) {
      setError('Paste at least 10 characters of text or upload a document.')
      return false
    }
    if (!textModel || !ttsModel) {
      setError('Models are still loading. Please wait.')
      return false
    }
    setError(null)
    return true
  }

  const startScript = async (autoGeneratePodcast: boolean) => {
    if (!validateInput()) return
    setSubmitting(true)
    setError(null)
    try {
      const inputFile =
        file ?? new File([content.trim()], 'input.txt', { type: 'text/plain' })
      await createScript(projectId, {
        file: inputFile,
        speakerVoices: speakers.map((s) => s.voiceId),
        numSpeakers: speakers.length,
        textModel,
        temperature,
        ttsModel,
        episodeTitle,
        autoGeneratePodcast,
      })
      navigate(`/projects/${projectId}`)
      void qc.invalidateQueries({ queryKey: ['projects', projectId] })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start script generation.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">New podcast</h1>
          <p className="mt-1 text-sm text-gray-500">
            Upload a long document, pick your voices, and generate multi-speaker audio
            {project ? ` · ${project.name}` : ''}
          </p>
        </div>
        <Button variant="secondary" onClick={() => navigate(`/projects/${projectId}`)}>
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-6">
          <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Sparkles className="h-4 w-4 text-brand" />
              Generation settings
            </h2>

            <label className="mt-4 block text-xs font-medium text-gray-500">Writing model</label>
            <select
              value={textModel}
              onChange={(e) => setTextModel(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            >
              {textModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>

            <label className="mt-4 flex items-center justify-between text-xs font-medium text-gray-500">
              Creativity
              <span className="rounded bg-brand-light px-2 py-0.5 text-brand-dark">
                {temperature.toFixed(2)}
              </span>
            </label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              className="mt-2 w-full accent-brand"
            />

            <label className="mt-4 block text-xs font-medium text-gray-500">TTS model</label>
            <select
              value={ttsModel}
              onChange={(e) => setTtsModel(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
            >
              {ttsModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.id}
                </option>
              ))}
            </select>
          </section>

          <section className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Headphones className="h-4 w-4 text-brand" />
              Voice selection
            </h2>
            <div className="mt-4">
              {voices.length > 0 ? (
                <VoiceSelector speakers={speakers} voices={voices} onChange={setSpeakers} />
              ) : (
                <p className="text-sm text-gray-400">Loading voices…</p>
              )}
            </div>
          </section>
        </aside>

        <main className="rounded-2xl border border-gray-100 bg-white p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Headphones className="h-4 w-4 text-brand" />
            Text → Podcast → Multi-speaker audio
          </h2>

          <label className="mt-6 block text-xs font-medium text-gray-500">Episode title</label>
          <input
            type="text"
            value={episodeTitle}
            onChange={(e) => setEpisodeTitle(e.target.value)}
            placeholder="e.g. Azure fundamentals, episode 1"
            className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm"
          />

          <label className="mt-6 block text-xs font-medium text-gray-500">Input content</label>
          <div className="mt-2">
            <FileDropzone
              content={content}
              onContentChange={setContent}
              file={file}
              onFileChange={setFile}
            />
          </div>

          {error && (
            <div className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <div className="mt-6 flex flex-wrap gap-3">
            <Button onClick={() => void startScript(true)} disabled={submitting}>
              <Sparkles className="h-4 w-4" />
              Generate podcast audio
            </Button>
            <Button
              variant="secondary"
              onClick={() => void startScript(false)}
              disabled={submitting}
            >
              <Wand2 className="h-4 w-4" />
              Create &amp; edit script first
            </Button>
          </div>
        </main>
      </div>
    </AppLayout>
  )
}
