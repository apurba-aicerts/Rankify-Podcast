import type { QueryClient } from '@tanstack/react-query'

import type { PodcastScript, ProjectDetail, ProjectItem } from '../types/api'



/** Immediately swap a script item for a generating-audio podcast item. */

export function applyOptimisticPodcastGeneration(

  qc: QueryClient,

  projectId: string,

  scriptId: string,

  script: PodcastScript,

): void {

  const now = new Date().toISOString()

  const optimisticItem: ProjectItem = {
    id: crypto.randomUUID(),
    kind: 'podcast',
    phase: 'generating_audio',
    title: script.title,
    description: script.description,
    error_message: null,
    audio_url: null,
    script,
    tts_model: null,
    text_model: null,
    script_id: scriptId,
    created_at: now,
    updated_at: now,
  }



  qc.setQueryData<ProjectDetail>(['projects', projectId], (old) => {

    if (!old) return old

    const items = [optimisticItem, ...old.items.filter((i) => i.script_id !== scriptId)]

    return {

      ...old,

      counts: {

        ...old.counts,

        total_items: items.length,

      },

      items,

    }

  })

}


