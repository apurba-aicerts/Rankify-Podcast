import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Headphones, Loader2, Plus } from 'lucide-react'
import { AppLayout } from '../components/layout/AppLayout'
import { ProjectItemCard } from '../components/ProjectItemCard'
import { Button } from '../components/ui/Button'
import { EmptyState, LoadingOverlay, StatCard } from '../components/ui/Shared'
import { useProject } from '../hooks/useProjects'

export function ProjectPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { data: project, isLoading, isFetching, error: projectError } = useProject(projectId)

  const items = project?.items ?? []
  const hasContent = items.length > 0

  if (isLoading && !project) {
    return (
      <AppLayout>
        <LoadingOverlay message="Loading project…" />
      </AppLayout>
    )
  }

  if (projectError || !project) {
    return (
      <AppLayout>
        <div className="rounded-xl bg-red-50 p-4 text-sm text-red-700">Project not found.</div>
        <Link to="/" className="mt-4 inline-block text-sm text-brand">
          Back to dashboard
        </Link>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-gray-900">{project.name}</h1>
            {isFetching && (
              <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Updating…
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {project.description?.trim() || 'All podcasts created in this project'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/')}>
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </Button>
          <Button onClick={() => navigate(`/projects/${projectId}/new`)}>
            <Plus className="h-4 w-4" />
            New podcast
          </Button>
        </div>
      </div>

      <div className="mt-8 grid max-w-2xl gap-4 sm:grid-cols-2">
        <StatCard label="Finished" value={project.counts.finished_podcasts} icon={Headphones} />
        <StatCard label="In progress" value={project.counts.unfinished} icon={Headphones} />
      </div>

      <div className="mt-8">
        {!hasContent ? (
          <EmptyState
            icon={<Headphones className="h-8 w-8 text-brand" />}
            title="No podcasts in this project yet"
            description="Upload a big PDF or paste a script, pick your speakers and produce the episode."
            action={
              <Button onClick={() => navigate(`/projects/${projectId}/new`)}>
                <Plus className="h-4 w-4" />
                Create the first podcast
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {items.map((item) => (
              <ProjectItemCard key={item.id} item={item} projectId={projectId} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
