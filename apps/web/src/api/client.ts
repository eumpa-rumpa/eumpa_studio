import type { HealthResponse, Project } from "./types";

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
