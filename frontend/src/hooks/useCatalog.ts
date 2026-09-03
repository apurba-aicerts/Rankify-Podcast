import { useQuery } from '@tanstack/react-query'
import * as voicesApi from '../api/voices'
import * as modelsApi from '../api/models'

export function useVoices() {
  return useQuery({
    queryKey: ['voices'],
    queryFn: voicesApi.listVoices,
    staleTime: 1000 * 60 * 30,
  })
}

export function useTextModels() {
  return useQuery({
    queryKey: ['models', 'text'],
    queryFn: modelsApi.listTextModels,
    staleTime: 1000 * 60 * 30,
  })
}

export function useTtsModels() {
  return useQuery({
    queryKey: ['models', 'tts'],
    queryFn: modelsApi.listTtsModels,
    staleTime: 1000 * 60 * 30,
  })
}
