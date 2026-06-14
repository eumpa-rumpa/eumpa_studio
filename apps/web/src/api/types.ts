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

/** A generation/render attempt returned from the API */
export interface Attempt {
  id: string;
  shot_id: string;
  status: string;
  prompt_ko: string | null;
  prompt_en: string | null;
  review_note: string | null;
  created_at: string;
}
