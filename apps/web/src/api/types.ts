/** Response from GET /api/health */
export interface HealthResponse {
  backend: string;
  database: string;
  comfyui: string;
  codex_cli: string;
}

/** A project returned from the API */
export interface Project {
  id: string;
  name: string;
  audio_storage_backend: string | null;
  audio_relative_path: string | null;
  lyrics_text: string | null;
  lyrics_storage_backend: string | null;
  lyrics_relative_path: string | null;
  visual_bible_text: string | null;
  visual_bible_storage_backend: string | null;
  visual_bible_relative_path: string | null;
  default_comfyui_server: string | null;
  created_at: string;
  updated_at: string;
}

/** A background job returned from the API */
export interface Job {
  id: string;
  type: string;
  target_entity_type: string | null;
  target_entity_id: string | null;
  status: string;
  logs: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

/** Summary of a shot attempt embedded in shot responses */
export interface AttemptSummary {
  id: string;
  status: string;
  image_storage_backend: string | null;
  image_relative_path: string | null;
  prompt_ko: string | null;
  prompt_en: string | null;
}

/** A shot returned from the API */
export interface Shot {
  id: string;
  project_id: string;
  order: number;
  start_time: number;
  end_time: number;
  duration: number;
  speaker: string | null;
  lyrics_text: string | null;
  shot_note: string | null;
  status: string;
  active_attempt_id: string | null;
  active_attempt: AttemptSummary | null;
  attempt_count: number;
  created_at: string;
  updated_at: string;
}
