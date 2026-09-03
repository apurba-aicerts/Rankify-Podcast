import { AlertCircle, FileText, Loader2, Wand2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { StoredScript } from '../types/api'
import { cn } from '../lib/utils'
import { Button } from './ui/Button'
import * as scriptsApi from '../api/scripts'
import { useQueryClient } from '@tanstack/react-query'

interface ScriptCardProps {
  script: StoredScript
  projectId: string
}

export function ScriptCard({ script, projectId }: ScriptCardProps) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const isGenerating = script.status === 'generating'
  const isFailed = script.status === 'failed'
  const isReady = script.status === 'ready'

  const dismiss = async () => {
    await scriptsApi.deleteScript(projectId, script.id)
    await qc.invalidateQueries({ queryKey: ['projects', projectId] })
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
            <FileText className="h-5 w-5 text-brand" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Script</p>
          <h3 className="font-semibold text-gray-900">{script.title}</h3>
          {script.description && isReady && (
            <p className="mt-1 line-clamp-2 text-sm text-gray-500">{script.description}</p>
          )}
          {isGenerating && (
            <p className="mt-2 flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin text-brand" />
              Writing script…
            </p>
          )}
          {isFailed && (
            <p className="mt-2 text-sm text-red-600">{script.error_message ?? 'Script failed.'}</p>
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

      {isReady && (
        <Button
          className="mt-4 w-full"
          variant="secondary"
          onClick={() => navigate(`/projects/${projectId}/scripts/${script.id}`)}
        >
          <Wand2 className="h-4 w-4" />
          Review &amp; edit script
        </Button>
      )}

      {isGenerating && (
        <div className="mt-4 flex h-10 items-center justify-center rounded-xl bg-gray-100 text-xs text-gray-400">
          Editor opens when script is ready
        </div>
      )}
    </div>
  )
}
