import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Headphones, Layers, Loader, Plus } from 'lucide-react'
import type { Project } from '../types/api'
import { AppLayout } from '../components/layout/AppLayout'
import { NewProjectCard, ProjectCard } from '../components/ProjectCard'
import { Button } from '../components/ui/Button'
import { LoadingOverlay, Modal, StatCard } from '../components/ui/Shared'
import {
  useCreateProject,
  useDeleteProject,
  useProjects,
  useUpdateProject,
} from '../hooks/useProjects'

function ProjectFormFields({
  name,
  description,
  onNameChange,
  onDescriptionChange,
}: {
  name: string
  description: string
  onNameChange: (v: string) => void
  onDescriptionChange: (v: string) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-gray-500">Project name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Project name"
          className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
          autoFocus
        />
      </div>
      <div>
        <label className="text-xs font-medium text-gray-500">
          Short description <span className="text-gray-400">(optional)</span>
        </label>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="What is this project about?"
          rows={3}
          className="mt-1 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
        />
      </div>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading, isFetching, error } = useProjects()
  const createProject = useCreateProject()
  const updateProject = useUpdateProject()
  const deleteProject = useDeleteProject()

  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Project | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  const projects = data?.projects ?? []
  const hasData = Boolean(data)

  const resetForm = () => {
    setName('')
    setDescription('')
  }

  const openCreate = () => {
    resetForm()
    setCreateOpen(true)
  }

  const openEdit = (project: Project) => {
    setName(project.name)
    setDescription(project.description ?? '')
    setEditTarget(project)
  }

  useEffect(() => {
    if (!editTarget) resetForm()
  }, [editTarget])

  const handleCreate = async () => {
    const trimmed = name.trim()
    if (!trimmed) return
    const project = await createProject.mutateAsync({
      name: trimmed,
      description: description.trim() || undefined,
    })
    setCreateOpen(false)
    resetForm()
    navigate(`/projects/${project.id}`)
  }

  const handleUpdate = async () => {
    if (!editTarget) return
    const trimmed = name.trim()
    if (!trimmed) return
    await updateProject.mutateAsync({
      projectId: editTarget.id,
      body: {
        name: trimmed,
        description: description.trim(),
      },
    })
    setEditTarget(null)
    resetForm()
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    await deleteProject.mutateAsync(deleteTarget.id)
    setDeleteTarget(null)
  }

  const isBusy =
    createProject.isPending || updateProject.isPending || deleteProject.isPending

  // Only blank the page on the first load — keep cached UI while refetching
  // (e.g. navigating back while podcasts are generating).
  if (isLoading && !hasData) {
    return (
      <AppLayout>
        <LoadingOverlay message="Loading projects…" />
      </AppLayout>
    )
  }

  if (error && !hasData) {
    return (
      <AppLayout>
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
          Failed to load projects. Is the API running on port 8001?
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-gray-900">Dashboard</h1>
            {isFetching && hasData && (
              <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
                <Loader className="h-3.5 w-3.5 animate-spin" />
                Updating…
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Your projects and everything produced inside them
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <StatCard label="Projects" value={data?.total ?? 0} icon={Layers} />
        <StatCard label="Finished podcasts" value={data?.totals.finished_podcasts ?? 0} icon={Headphones} />
        <StatCard label="In progress" value={data?.totals.unfinished ?? 0} icon={Loader} />
      </div>

      <h2 className="mt-10 text-lg font-semibold text-gray-900">Projects</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onOpen={() => navigate(`/projects/${project.id}`)}
            onEdit={() => openEdit(project)}
            onDelete={() => setDeleteTarget(project)}
          />
        ))}
        <NewProjectCard onClick={openCreate} />
      </div>

      <Modal open={createOpen} title="New project" onClose={() => setCreateOpen(false)}>
        <ProjectFormFields
          name={name}
          description={description}
          onNameChange={setName}
          onDescriptionChange={setDescription}
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setCreateOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => void handleCreate()} disabled={!name.trim() || createProject.isPending}>
            Create
          </Button>
        </div>
      </Modal>

      <Modal
        open={editTarget !== null}
        title="Edit project"
        onClose={() => setEditTarget(null)}
      >
        <ProjectFormFields
          name={name}
          description={description}
          onNameChange={setName}
          onDescriptionChange={setDescription}
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setEditTarget(null)}>
            Cancel
          </Button>
          <Button onClick={() => void handleUpdate()} disabled={!name.trim() || updateProject.isPending}>
            Save
          </Button>
        </div>
      </Modal>

      <Modal
        open={deleteTarget !== null}
        title={`Delete “${deleteTarget?.name ?? ''}”?`}
        onClose={() => setDeleteTarget(null)}
      >
        <p className="text-sm text-gray-600">
          This will permanently delete this project and{' '}
          <strong>all podcasts, scripts, and audio files</strong> inside it. This cannot be
          undone.
        </p>
        {deleteTarget && deleteTarget.counts.total_items > 0 && (
          <p className="mt-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
            This project contains {deleteTarget.counts.finished_podcasts} finished podcast
            {deleteTarget.counts.finished_podcasts === 1 ? '' : 's'}
            {deleteTarget.counts.unfinished > 0
              ? ` and ${deleteTarget.counts.unfinished} in-progress item${deleteTarget.counts.unfinished === 1 ? '' : 's'}`
              : ''}
            .
          </p>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            className="bg-red-600 text-white hover:bg-red-700"
            onClick={() => void handleDelete()}
            disabled={deleteProject.isPending}
          >
            Delete project
          </Button>
        </div>
      </Modal>

      {isBusy && <LoadingOverlay message="Saving…" />}
    </AppLayout>
  )
}
