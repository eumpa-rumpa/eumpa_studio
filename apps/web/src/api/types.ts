/** Response from GET /api/health */
export interface HealthResponse {
  backend: string;
  database: string;
  comfyui: string;
  codex_cli: string;
}

/** Studio-wide prompt setting returned from settings routes */
export interface PromptSystemDefault {
  system_prompt: string;
  is_custom: boolean;
  updated_at: string | null;
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

/** A ComfyUI workflow template available for rendering */
export interface WorkflowTemplate {
  id: string;
  name: string;
  json_path: string;
  file_hash: string | null;
  version: string | null;
  compatibility_notes: string | null;
  is_available: boolean;
  validation_error: string | null;
  created_at: string;
  updated_at: string;
}

/** A render execution mode for a workflow template */
export interface ExecutionMode {
  id: string;
  workflow_template_id: string;
  name: string;
  required_inputs: string | null;
  optional_inputs: string | null;
  node_bindings: string | null;
  validation_rules: string | null;
  exposed_params: string | null;
  created_at: string;
  updated_at: string;
}

/** Summary of a shot attempt embedded in shot responses */
export interface AttemptSummary {
  id: string;
  status: string;
  image_storage_backend: string | null;
  image_relative_path: string | null;
  prompt_ko: string | null;
  prompt_en: string | null;
  output_metadata: string | null;
  video_url?: string | null;
}

/** Full attempt detail returned from shot attempt routes */
export interface Attempt {
  id: string;
  shot_id: string;
  parent_attempt_id: string | null;
  image_storage_backend: string | null;
  image_relative_path: string | null;
  end_image_storage_backend: string | null;
  end_image_relative_path: string | null;
  input_video_storage_backend: string | null;
  input_video_relative_path: string | null;
  shot_note_snapshot: string | null;
  prompt_ko: string | null;
  prompt_en: string | null;
  workflow_template_id: string | null;
  execution_mode_id: string | null;
  param_overrides: string | null;
  seed: number | null;
  workflow_snapshot: string | null;
  comfyui_prompt_id: string | null;
  output_metadata: string | null;
  review_note: string | null;
  status: string;
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
