import { apiFetch } from './client'
import type { Podcast, PodcastListResponse, PodcastSummary } from '../types/api'

export interface PodcastUpdateBody {
  title?: string
  description?: string
}

export function listPodcasts(projectId: string) {
  return apiFetch<PodcastListResponse>(`/projects/${projectId}/podcasts`)
}

export function getPodcast(projectId: string, podcastId: string) {
  return apiFetch<Podcast>(`/projects/${projectId}/podcasts/${podcastId}`)
}

export function updatePodcast(
  projectId: string,
  podcastId: string,
  body: PodcastUpdateBody,
) {
  return apiFetch<PodcastSummary>(`/projects/${projectId}/podcasts/${podcastId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deletePodcast(projectId: string, podcastId: string) {
  return apiFetch<void>(`/projects/${projectId}/podcasts/${podcastId}`, {
    method: 'DELETE',
  })
}
