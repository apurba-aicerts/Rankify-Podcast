import { apiFetch } from './client'
import type { VoicesResponse } from '../types/api'

export function listVoices() {
  return apiFetch<VoicesResponse>('/voices')
}
