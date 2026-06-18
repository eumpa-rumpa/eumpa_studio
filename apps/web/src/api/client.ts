import type {
  Attempt,
  Asset,
  ExecutionMode,
  HealthResponse,
  Job,
  Project,
  Shot,
  WorkflowTemplate,
} from "./types";

const BASE_URL = "/api";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      } else if (Array.isArray(errorBody.detail)) {
        message = errorBody.detail
          .map((item) => {
            if (typeof item === "string") return item;
            if (
              item &&
              typeof item === "object" &&
              "msg" in item &&
              typeof item.msg === "string"
            ) {
              return item.msg;
            }
            return JSON.stringify(item);
          })
          .join("; ");
      }
    } catch {
      // Keep the HTTP status fallback when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  return readJson<T>(response);
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return readJson<T>(response);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson<T>(response);
}

async function deleteRequest(path: string): Promise<void> {
  const response = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  if (!response.ok) {
    let message = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      if (typeof errorBody.detail === "string") {
        message = errorBody.detail;
      }
    } catch {
      // Keep the HTTP status fallback when the response is not JSON.
    }
    throw new Error(message);
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/health");
}

export async function fetchProjects(): Promise<Project[]> {
  return get<Project[]>("/projects");
}

export async function fetchProject(id: string): Promise<Project> {
  return get<Project>(`/projects/${id}`);
}

export async function fetchJobs(): Promise<Job[]> {
  return get<Job[]>("/jobs");
}

export async function fetchWorkflowTemplates(): Promise<WorkflowTemplate[]> {
  return get<WorkflowTemplate[]>("/workflows/templates");
}

export interface SkillWorkflowBootstrap {
  template: WorkflowTemplate;
  mode: ExecutionMode;
}

export async function bootstrapLtxLipSyncWorkflow(): Promise<SkillWorkflowBootstrap> {
  return postJson<SkillWorkflowBootstrap>("/workflows/skill-defaults/ltx-lipsync", {});
}

export async function fetchExecutionModes(templateId: string): Promise<ExecutionMode[]> {
  return get<ExecutionMode[]>(
    `/workflows/templates/${encodeURIComponent(templateId)}/modes`,
  );
}

export async function fetchShots(projectId: string): Promise<Shot[]> {
  const params = new URLSearchParams({ project_id: projectId });
  return get<Shot[]>(`/shots?${params.toString()}`);
}

export async function enqueueAlignment(projectId: string): Promise<Job> {
  return postJson<Job>(`/projects/${encodeURIComponent(projectId)}/align`, {});
}

export interface CreateShotBody {
  order: number;
  start_time: number;
  end_time: number;
  duration?: number;
  speaker?: string | null;
  lyrics_text?: string | null;
  shot_note?: string | null;
  status?: string;
}

export async function createShot(
  projectId: string,
  body: CreateShotBody,
): Promise<Shot> {
  return postJson<Shot>(`/projects/${encodeURIComponent(projectId)}/shots`, body);
}

export async function fetchShotAttempts(shotId: string): Promise<Attempt[]> {
  return get<Attempt[]>(`/shots/${shotId}/attempts`);
}

export interface CreateAttemptBody {
  image_storage_backend?: string | null;
  image_relative_path?: string | null;
  shot_note_snapshot?: string | null;
  prompt_ko?: string | null;
  prompt_en?: string | null;
  workflow_template_id?: string | null;
  execution_mode_id?: string | null;
  param_overrides?: string | null;
  seed?: number | null;
}

export async function createAttempt(
  shotId: string,
  body: CreateAttemptBody = {},
): Promise<Attempt> {
  return postJson<Attempt>(
    `/shots/${encodeURIComponent(shotId)}/attempts`,
    body,
  );
}

export async function updateShot(
  shotId: string,
  body: Partial<Pick<Shot, "start_time" | "end_time" | "shot_note" | "active_attempt_id" | "status">>,
): Promise<Shot> {
  return patch<Shot>(`/shots/${shotId}`, body);
}

export async function updateAttemptReviewNote(
  shotId: string,
  attemptId: string,
  reviewNote: string,
): Promise<Attempt> {
  return patch<Attempt>(`/shots/${shotId}/attempts/${attemptId}`, {
    review_note: reviewNote,
  });
}

export async function createProject(formData: FormData): Promise<Project> {
  const response = await fetch(`${BASE_URL}/projects`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<Project>;
}

export async function generatePrompt(attemptId: string): Promise<Attempt> {
  return postJson<Attempt>("/prompts/generate", { attempt_id: attemptId });
}

export interface SavePromptBody {
  image_storage_backend?: string | null;
  image_relative_path?: string | null;
  end_image_storage_backend?: string | null;
  end_image_relative_path?: string | null;
  input_video_storage_backend?: string | null;
  input_video_relative_path?: string | null;
  shot_note_snapshot?: string | null;
  prompt_ko?: string | null;
  prompt_en?: string | null;
  workflow_template_id?: string | null;
  execution_mode_id?: string | null;
  param_overrides?: string | null;
  seed?: number | null;
  review_note?: string | null;
}

export async function savePrompt(
  shotId: string,
  attemptId: string,
  body: SavePromptBody,
): Promise<Attempt> {
  const encodedShotId = encodeURIComponent(shotId);
  const encodedAttemptId = encodeURIComponent(attemptId);
  return patch<Attempt>(
    `/shots/${encodedShotId}/attempts/${encodedAttemptId}`,
    body,
  );
}

export async function fetchAssets(projectId: string): Promise<Asset[]> {
  return get<Asset[]>(`/assets/${projectId}`);
}

export async function enqueueRender(shotId: string, attemptId: string): Promise<Job> {
  return postJson<Job>(
    `/shots/${encodeURIComponent(shotId)}/attempts/${encodeURIComponent(attemptId)}/render`,
    {},
  );
}

export async function duplicateAttempt(
  shotId: string,
  attemptId: string,
): Promise<Attempt> {
  return postJson<Attempt>(
    `/shots/${encodeURIComponent(shotId)}/attempts/${encodeURIComponent(attemptId)}/duplicate`,
    {},
  );
}

export async function deleteAttempt(shotId: string, attemptId: string): Promise<void> {
  return deleteRequest(
    `/shots/${encodeURIComponent(shotId)}/attempts/${encodeURIComponent(attemptId)}`,
  );
}
