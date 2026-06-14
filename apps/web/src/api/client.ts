import type { HealthResponse, Job } from "./types";

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

export async function fetchJobs(): Promise<Job[]> {
  return get<Job[]>("/jobs");
}
