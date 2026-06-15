import type { Attempt, Asset, HealthResponse, Job, Project, Shot } from "./types";

const BASE_URL = "/api";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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

export async function fetchShots(projectId: string): Promise<Shot[]> {
  const params = new URLSearchParams({ project_id: projectId });
  return get<Shot[]>(`/shots?${params.toString()}`);
}

export async function fetchShotAttempts(shotId: string): Promise<Attempt[]> {
  return get<Attempt[]>(`/shots/${shotId}/attempts`);
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
  prompt_ko?: string | null;
  prompt_en?: string | null;
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
