import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ProjectUpdateBody, ProjectWriteBody } from '../api/projects'
import * as projectsApi from '../api/projects'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.listProjects,
  })
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => projectsApi.getProject(projectId),
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const detail = query.state.data
      if (!detail) return false
      const busy = detail.items.some(
        (i) => i.phase === 'writing_script' || i.phase === 'generating_audio',
      )
      return busy ? 3000 : false
    },
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ProjectWriteBody) => projectsApi.createProject(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export function useUpdateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: string; body: ProjectUpdateBody }) =>
      projectsApi.updateProject(projectId, body),
    onSuccess: (_data, { projectId }) => {
      void qc.invalidateQueries({ queryKey: ['projects'] })
      void qc.invalidateQueries({ queryKey: ['projects', projectId] })
    },
  })
}

export function useDeleteProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => projectsApi.deleteProject(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}
