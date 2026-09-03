import { useQuery } from '@tanstack/react-query'
import * as scriptsApi from '../api/scripts'

export function useScripts(projectId: string) {
  return useQuery({
    queryKey: ['scripts', projectId],
    queryFn: () => scriptsApi.listScripts(projectId),
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const scripts = query.state.data?.scripts ?? []
      return scripts.some((s) => s.status === 'generating') ? 3000 : false
    },
  })
}

export function useScript(projectId: string, scriptId: string) {
  return useQuery({
    queryKey: ['scripts', projectId, scriptId],
    queryFn: () => scriptsApi.getScript(projectId, scriptId),
    enabled: Boolean(projectId) && Boolean(scriptId),
    refetchInterval: (query) => {
      const script = query.state.data
      return script?.status === 'generating' ? 3000 : false
    },
  })
}
