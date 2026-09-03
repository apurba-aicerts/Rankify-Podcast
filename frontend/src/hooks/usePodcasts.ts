import { useQuery } from '@tanstack/react-query'
import * as podcastsApi from '../api/podcasts'

export function usePodcasts(projectId: string) {
  return useQuery({
    queryKey: ['podcasts', projectId],
    queryFn: () => podcastsApi.listPodcasts(projectId),
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const podcasts = query.state.data?.podcasts ?? []
      return podcasts.some((p) => p.status === 'generating') ? 3000 : false
    },
  })
}
