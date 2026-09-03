import { Pencil, Plus, Trash2 } from 'lucide-react'
import type { Project } from '../types/api'
import { cn, getInitials } from '../lib/utils'

interface ProjectCardProps {
  project: Project
  onOpen: () => void
  onEdit: () => void
  onDelete: () => void
}

export function ProjectCard({ project, onOpen, onEdit, onDelete }: ProjectCardProps) {
  return (
    <div className="relative flex w-full flex-col rounded-2xl border border-gray-100 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="absolute right-3 top-3 flex gap-1">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onEdit()
          }}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          aria-label="Edit project"
        >
          <Pencil className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
          }}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
          aria-label="Delete project"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <button type="button" onClick={onOpen} className="flex w-full flex-col text-left">
        <div className="flex items-start gap-4 pr-14">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-light text-sm font-semibold text-brand-dark">
            {getInitials(project.name)}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-semibold text-gray-900">{project.name}</h3>
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">
              {project.description?.trim() || 'No description'}
            </p>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <span className="rounded-full border border-brand/30 bg-brand-light/50 px-3 py-1 text-xs font-medium text-brand-dark">
            {project.counts.finished_podcasts} finished
          </span>
          {project.counts.unfinished > 0 && (
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
              {project.counts.unfinished} in progress
            </span>
          )}
        </div>
      </button>
    </div>
  )
}

interface NewProjectCardProps {
  onClick: () => void
}

export function NewProjectCard({ onClick }: NewProjectCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex min-h-[140px] flex-col items-center justify-center rounded-2xl',
        'border-2 border-dashed border-gray-200 bg-white/60 p-5 transition-colors hover:border-brand/40 hover:bg-brand-light/20',
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-900 text-white">
        <Plus className="h-6 w-6" />
      </div>
      <span className="mt-3 text-sm font-medium text-brand">New project</span>
    </button>
  )
}
