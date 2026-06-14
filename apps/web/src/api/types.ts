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

/** An asset (image/file) belonging to a project */
export interface Asset {
  id: string;
  project_id: string;
  name: string;
  storage_backend: string;
  relative_path: string;
  mime_type: string | null;
  created_at: string;
  url: string;
  thumb_url: string;
}

/** A shot attempt (draft) returned from the API */
export interface Attempt {
  id: string;
  shot_id: string;
  status: string;
  image_storage_backend: string | null;
  image_relative_path: string | null;
  created_at: string;
}
