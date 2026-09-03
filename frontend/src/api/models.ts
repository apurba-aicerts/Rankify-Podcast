import { apiFetch } from './client'
import type { TextModelsResponse, TtsModelsResponse } from '../types/api'

export function listTextModels() {
  return apiFetch<TextModelsResponse>('/models/text')
}

export function listTtsModels() {
  return apiFetch<TtsModelsResponse>('/models/tts')
}
