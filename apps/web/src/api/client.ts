import type { Attempt, HealthResponse, Job, Project } from "./types";

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

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson<T>(response);
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readJson<T>(response);
}

export async function fetchHealth(): Promise<HealthResponse> {
  return get<HealthResponse>("/health");
}

export async function fetchJobs(): Promise<Job[]> {
  return get<Job[]>("/jobs");
}

export async function fetchProjects(): Promise<Project[]> {
  return get<Project[]>("/projects");
}

export async function fetchProject(id: string): Promise<Project> {
  return get<Project>(`/projects/${id}`);
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
  return patchJson<Attempt>(
    `/shots/${encodedShotId}/attempts/${encodedAttemptId}`,
    body,
  );
}
