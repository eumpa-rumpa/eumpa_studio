/** Response from GET /api/health */
export interface HealthResponse {
  status: string;
}

export type JobStatus = "pending" | "running" | "done" | "failed";

/** Response from GET /api/jobs */
export interface Job {
  id: string;
  type: string;
  target_entity_type: string | null;
  target_entity_id: string | null;
  status: JobStatus;
  logs: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}
