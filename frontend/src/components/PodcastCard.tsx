import { AlertCircle, Headphones, Loader2, X } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import type { PodcastSummary } from '../types/api'
import { formatDate } from '../lib/utils'
import { cn } from '../lib/utils'
import * as podcastsApi from '../api/podcasts'

interface PodcastCardProps {
  podcast: PodcastSummary
  projectId: string
}

export function PodcastCard({ podcast, projectId }: PodcastCardProps) {
  const qc = useQueryClient()
  const isGenerating = podcast.status === 'generating'
  const isFailed = podcast.status === 'failed'

  const dismiss = async () => {
    await podcastsApi.deletePodcast(projectId, podcast.id)
      await qc.invalidateQueries({ queryKey: ['projects', projectId] })
      await qc.invalidateQueries({ queryKey: ['projects'] })
  }

  return (
    <div
      className={cn(
        'rounded-2xl border bg-white p-5 shadow-sm',
        isFailed ? 'border-red-200' : 'border-gray-100',
        isGenerating && 'opacity-75',
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
          ) : (
            <Headphones className="h-5 w-5 text-brand" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Podcast</p>
          <h3 className="font-semibold text-gray-900">{podcast.title}</h3>
          {podcast.description && !isGenerating && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">{podcast.description}</p>
          )}
          {isGenerating && (
            <p className="mt-2 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin text-brand" />
              Generating audio…
            </p>
          )}
          {isFailed && (
            <p className="mt-2 text-sm text-red-600">{podcast.error_message ?? 'Generation failed.'}</p>
          )}
          {!isGenerating && (
            <p className="mt-2 text-xs text-gray-400">{formatDate(podcast.created_at)}</p>
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

      {podcast.status === 'ready' && podcast.audio_url && (
        <audio controls className="mt-4 w-full" src={podcast.audio_url} preload="none">
          Your browser does not support audio playback.
        </audio>
      )}

      {isGenerating && (
        <div className="mt-4 flex h-10 items-center justify-center rounded-xl bg-gray-100 text-xs text-gray-400">
          Audio player will appear when ready
        </div>
      )}
    </div>
  )
}
