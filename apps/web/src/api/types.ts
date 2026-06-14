/** Response from GET /api/health */
export interface HealthResponse {
  backend: string;
  database: string;
  comfyui: string;
  codex_cli: string;
}
