import { apiFetch } from './client'
import type { Project, ProjectDetail, ProjectListResponse } from '../types/api'

export interface ProjectWriteBody {
  name: string
  description?: string
}

export interface ProjectUpdateBody {
  name?: string
  description?: string
}

export function listProjects() {
  return apiFetch<ProjectListResponse>('/projects')
}

export function getProject(projectId: string) {
  return apiFetch<ProjectDetail>(`/projects/${projectId}`)
}

export function createProject(body: ProjectWriteBody) {
  return apiFetch<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: body.name,
      description: body.description?.trim() || null,
    }),
  })
}

export function updateProject(projectId: string, body: ProjectUpdateBody) {
  return apiFetch<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      ...(body.name !== undefined ? { name: body.name } : {}),
      ...(body.description !== undefined
        ? { description: body.description.trim() || null }
        : {}),
    }),
  })
}

export function deleteProject(projectId: string) {
  return apiFetch<void>(`/projects/${projectId}`, { method: 'DELETE' })
}
