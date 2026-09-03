export interface Speaker {

  name: string

  voice_id: string

}



export interface DialogueTurn {

  speaker: string

  text: string

}



export interface PodcastScript {

  title: string

  description: string

  speakers: Speaker[]

  dialogue: DialogueTurn[]

}



export interface ProjectCounts {

  finished_podcasts: number

  unfinished: number

  total_items: number

}



export interface Project {
  id: string
  name: string
  description: string | null
  status: string
  counts: ProjectCounts
  created_at: string
  updated_at: string
}



export type ProjectItemPhase =

  | 'writing_script'

  | 'script_ready'

  | 'generating_audio'

  | 'ready'

  | 'failed'



export interface ProjectItem {
  id: string
  kind: 'script' | 'podcast'
  phase: ProjectItemPhase
  title: string
  description: string | null
  error_message: string | null
  audio_url: string | null
  script: PodcastScript | null
  tts_model: string | null
  text_model: string | null
  /** Script UUID — always set (equals id for script items, source script for podcast items). */
  script_id: string
  created_at: string
  updated_at: string
}



export interface ProjectDetail {
  id: string
  name: string
  description: string | null
  status: string
  counts: ProjectCounts
  items: ProjectItem[]
  created_at: string
  updated_at: string
}



export interface ProjectListResponse {

  projects: Project[]

  total: number

  totals: ProjectCounts

}



export interface PodcastSummary {

  id: string

  title: string

  description: string | null

  status: 'generating' | 'ready' | 'failed'

  error_message: string | null

  audio_url: string | null

  script_id: string | null

  created_at: string

}



export interface PodcastListResponse {

  podcasts: PodcastSummary[]

  total: number

}



export interface Podcast extends PodcastSummary {

  project_id: string

  s3_key: string | null

  tts_model: string

  tts_metadata: Record<string, unknown> | null

  podcast_script_snapshot: Record<string, unknown> | null

  updated_at: string

}



export interface StoredScript {

  id: string

  project_id: string

  title: string

  description: string | null

  status: 'generating' | 'ready' | 'failed' | 'published'

  error_message: string | null

  script: PodcastScript | null

  text_model: string

  tts_model: string

  source_filename: string | null

  auto_generate_podcast: boolean

  created_at: string

  updated_at: string

}



export interface ScriptListResponse {

  scripts: StoredScript[]

  total: number

}



export interface VoiceInfo {

  id: string

  name: string

  description: string

  s3_key: string | null

  audio_url: string | null

  sample_available: boolean

  sample_url: string | null

}



export interface VoicesResponse {

  voices: VoiceInfo[]

  total: number

}



export interface ModelInfo {

  id: string

  name: string

  description: string

}



export interface TextModelsResponse {

  models: ModelInfo[]

  total: number

  limit: number

  cached_at: string | null

}



export interface TtsModelsResponse {

  models: ModelInfo[]

  total: number

  limit: number

  cached_at: string | null

}



export interface GeneratePodcastResponse {

  success: boolean

  message: string

  podcast: PodcastSummary | null

}


