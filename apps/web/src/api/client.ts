import type { HealthResponse, Job, Project, Shot } from "./types";

const BASE_URL = "/api";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
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
