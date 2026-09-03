import { useState } from 'react'
import { AlertCircle, FileText, Headphones, Loader2, Wand2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import type { PodcastScript, ProjectItem } from '../types/api'
import { cn, formatDate } from '../lib/utils'
import { Button } from './ui/Button'
import { Modal } from './ui/Shared'
import * as podcastsApi from '../api/podcasts'
import * as scriptsApi from '../api/scripts'

interface ProjectItemCardProps {
  item: ProjectItem
  projectId: string
}

function ScriptViewModal({
  script,
  open,
  onClose,
}: {
  script: PodcastScript
  open: boolean
  onClose: () => void
}) {
  return (
    <Modal
      open={open}
      title={script.title}
      onClose={onClose}
      panelClassName="max-h-[85vh] max-w-2xl overflow-y-auto"
    >
      {script.description && (
        <p className="text-sm text-gray-500">{script.description}</p>
      )}

      <div className="mt-4">
        <h3 className="text-sm font-semibold text-gray-900">Speakers</h3>
        <ul className="mt-2 space-y-1 text-sm text-gray-600">
          {script.speakers.map((speaker, i) => (
            <li key={i}>
              {speaker.name} <span className="text-gray-400">({speaker.voice_id})</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <h3 className="text-sm font-semibold text-gray-900">Dialogue</h3>
        <div className="mt-2 space-y-2">
          {script.dialogue.map((turn, i) => (
            <div key={i} className="rounded-xl bg-gray-50 p-3 text-sm">
              <span className="font-medium text-gray-900">{turn.speaker}</span>
              <p className="mt-1 text-gray-600">{turn.text}</p>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  )
}

export function ProjectItemCard({ item, projectId }: ProjectItemCardProps) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [viewScriptOpen, setViewScriptOpen] = useState(false)

  const isScript = item.kind === 'script'
  const isFailed = item.phase === 'failed'
  const isBusy = item.phase === 'writing_script' || item.phase === 'generating_audio'

  const dismiss = async () => {
    if (item.kind === 'script') {
      await scriptsApi.deleteScript(projectId, item.script_id)
    } else {
      await podcastsApi.deletePodcast(projectId, item.id)
    }
    await qc.invalidateQueries({ queryKey: ['projects', projectId] })
    await qc.invalidateQueries({ queryKey: ['projects'] })
  }

  const statusLabel =
    item.phase === 'writing_script'
      ? 'Writing script…'
      : item.phase === 'generating_audio'
        ? 'Generating audio…'
        : null

  return (
    <div
      className={cn(
        'rounded-2xl border bg-white p-5 shadow-sm',
        isFailed ? 'border-red-200' : 'border-gray-100',
        isBusy && 'opacity-75',
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
            isFailed ? 'bg-red-50' : 'bg-brand-light',
          )}
        >
          {isFailed ? (
            <AlertCircle className="h-5 w-5 text-red-500" />
          ) : isScript ? (
            <FileText className="h-5 w-5 text-brand" />
          ) : (
            <Headphones className="h-5 w-5 text-brand" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            {isScript ? 'Script' : 'Podcast'}
          </p>
          <h3 className="font-semibold text-gray-900">{item.title}</h3>
          {item.script && item.phase === 'script_ready' && (
            <p className="mt-1 text-xs text-gray-400">
              {item.script.dialogue.length} lines · {item.script.speakers.length} speakers
            </p>
          )}
          {item.description && item.phase === 'script_ready' && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">{item.description}</p>
          )}
          {item.description && item.phase === 'ready' && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">{item.description}</p>
          )}
          {statusLabel && (
            <p className="mt-2 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin text-brand" />
              {statusLabel}
            </p>
          )}
          {isFailed && (
            <p className="mt-2 text-sm text-red-600">{item.error_message ?? 'Generation failed.'}</p>
          )}
          {!isBusy && !isFailed && item.phase !== 'script_ready' && (
            <p className="mt-2 text-xs text-gray-400">{formatDate(item.created_at)}</p>
          )}
        </div>
        {isFailed && (
          <button
            type="button"
            onClick={() => void dismiss()}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {item.phase === 'script_ready' && (
        <Button
          className="mt-4 w-full"
          variant="secondary"
          onClick={() => navigate(`/projects/${projectId}/scripts/${item.script_id}`)}
        >
          <Wand2 className="h-4 w-4" />
          Review &amp; edit script
        </Button>
      )}

      {item.phase === 'ready' && item.audio_url && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <audio controls className="min-w-0 flex-1" src={item.audio_url} preload="none">
            Your browser does not support audio playback.
          </audio>
          {item.script && (
            <Button
              variant="secondary"
              className="shrink-0"
              onClick={() => setViewScriptOpen(true)}
            >
              <FileText className="h-4 w-4" />
              View script
            </Button>
          )}
        </div>
      )}

      {isBusy && (
        <div className="mt-4 flex h-10 items-center justify-center rounded-xl bg-gray-100 text-xs text-gray-400">
          {item.phase === 'writing_script'
            ? 'Editor opens when script is ready'
            : 'Audio player will appear when ready'}
        </div>
      )}

      {item.script && (
        <ScriptViewModal
          script={item.script}
          open={viewScriptOpen}
          onClose={() => setViewScriptOpen(false)}
        />
      )}
    </div>
  )
}
