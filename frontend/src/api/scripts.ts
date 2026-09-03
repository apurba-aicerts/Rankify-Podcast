import { apiFetch } from './client'
import type { GeneratePodcastResponse, PodcastScript, ScriptListResponse, StoredScript } from '../types/api'

export interface CreateScriptParams {
  file: File
  speakerVoices: string[]
  numSpeakers: number
  textModel: string
  temperature: number
  ttsModel: string
  episodeTitle?: string
  autoGeneratePodcast?: boolean
}

function buildScriptForm(params: CreateScriptParams): FormData {
  const form = new FormData()
  form.append('file', params.file)
  form.append('speaker_voices', params.speakerVoices.join(','))
  form.append('num_speakers', String(params.numSpeakers))
  form.append('text_model', params.textModel)
  form.append('temperature', String(params.temperature))
  form.append('tts_model', params.ttsModel)
  form.append('auto_generate_podcast', String(params.autoGeneratePodcast ?? false))
  if (params.episodeTitle?.trim()) {
    form.append('episode_title', params.episodeTitle.trim())
  }
  return form
}

export function createScript(projectId: string, params: CreateScriptParams) {
  return apiFetch<StoredScript>(`/projects/${projectId}/scripts`, {
    method: 'POST',
    body: buildScriptForm(params),
  })
}

export function listScripts(projectId: string) {
  return apiFetch<ScriptListResponse>(`/projects/${projectId}/scripts`)
}

export function getScript(projectId: string, scriptId: string) {
  return apiFetch<StoredScript>(`/projects/${projectId}/scripts/${scriptId}`)
}

export function updateScript(
  projectId: string,
  scriptId: string,
  body: {
    title?: string
    description?: string
    script?: PodcastScript
    tts_model?: string
  },
) {
  return apiFetch<StoredScript>(`/projects/${projectId}/scripts/${scriptId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteScript(projectId: string, scriptId: string) {
  return apiFetch<void>(`/projects/${projectId}/scripts/${scriptId}`, { method: 'DELETE' })
}

export function generatePodcastFromScript(
  projectId: string,
  scriptId: string,
  ttsModel?: string,
  script?: PodcastScript,
) {
  return apiFetch<GeneratePodcastResponse>(
    `/projects/${projectId}/scripts/${scriptId}/generate-podcast`,
    {
      method: 'POST',
      body: JSON.stringify({
        tts_model: ttsModel ?? null,
        script: script ?? null,
      }),
    },
  )
}
