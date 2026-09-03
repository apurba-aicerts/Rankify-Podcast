import { apiFetch } from './client'
import type { Podcast, PodcastListResponse } from '../types/api'

export function listPodcasts(projectId: string) {
  return apiFetch<PodcastListResponse>(`/projects/${projectId}/podcasts`)
}

export function getPodcast(projectId: string, podcastId: string) {
  return apiFetch<Podcast>(`/projects/${projectId}/podcasts/${podcastId}`)
}

export function deletePodcast(projectId: string, podcastId: string) {
  return apiFetch<void>(`/projects/${projectId}/podcasts/${podcastId}`, {
    method: 'DELETE',
  })
}
