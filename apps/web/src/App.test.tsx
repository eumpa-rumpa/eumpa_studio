import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";
import type { HealthResponse, Job, Project, Shot } from "./api/types";

const project: Project = {
  id: "project-1",
  name: "Persisted Project",
  audio_storage_backend: null,
  audio_relative_path: null,
  lyrics_text: null,
  lyrics_storage_backend: null,
  lyrics_relative_path: null,
  visual_bible_text: null,
  visual_bible_storage_backend: null,
  visual_bible_relative_path: null,
  default_comfyui_server: null,
  created_at: "2026-06-15T00:00:00Z",
  updated_at: "2026-06-15T00:00:00Z",
};

const health: HealthResponse = {
  backend: "ok",
  database: "ok",
  comfyui: "unavailable",
  codex_cli: "ok",
};

const queuedJob: Job = {
  id: "job-1",
  type: "align",
  target_entity_type: "project",
  target_entity_id: "project-1",
  status: "pending",
  logs: null,
  error: null,
  created_at: "2026-06-15T00:00:00Z",
  updated_at: "2026-06-15T00:00:00Z",
  started_at: null,
  finished_at: null,
};

const existingShot: Shot = {
  id: "shot-1",
  project_id: "project-1",
  order: 0,
  start_time: 0,
  end_time: 5,
  duration: 5,
  speaker: null,
  lyrics_text: null,
  shot_note: null,
  status: "Needs Input",
  active_attempt_id: null,
  active_attempt: null,
  attempt_count: 0,
  created_at: "2026-06-15T00:00:00Z",
  updated_at: "2026-06-15T00:00:00Z",
};

let jobs: Job[] = [];
let shots: Shot[] = [];

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

beforeEach(() => {
  localStorage.clear();
  jobs = [];
  shots = [];
  vi.spyOn(window, "fetch").mockImplementation((input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url === "/api/health") {
      return Promise.resolve(jsonResponse(health));
    }
    if (url === "/api/projects") {
      return Promise.resolve(jsonResponse([project]));
    }
    if (url === "/api/projects/project-1") {
      return Promise.resolve(jsonResponse(project));
    }
    if (url === "/api/jobs") {
      return Promise.resolve(jsonResponse(jobs));
    }
    if (url === "/api/shots?project_id=project-1") {
      return Promise.resolve(jsonResponse(shots));
    }
    if (url === "/api/projects/project-1/align" && init?.method === "POST") {
      return Promise.resolve(jsonResponse({ id: "job-1", type: "align" }, { status: 201 }));
    }

    return Promise.reject(new Error(`Unhandled request: ${url}`));
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("App workspace flow", () => {
  test("restores the last selected project after reload", async () => {
    localStorage.setItem("eumpa-studio:selected-project-id", "project-1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Persisted Project" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Create a Project" })).not.toBeInTheDocument();
  });

  test("shows empty-workspace actions for alignment and manual shot creation", async () => {
    const user = userEvent.setup();

    render(<App />);

    const openProject = await screen.findByRole("button", { name: /Persisted Project/ });
    await user.click(openProject);

    await waitFor(() => {
      expect(screen.getByText("No shots yet. Run alignment to generate shots.")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Run alignment" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add manual shot" })).toBeInTheDocument();
  });

  test("keeps production actions visible when a project already has shots", async () => {
    shots = [existingShot];
    jobs = [queuedJob];
    localStorage.setItem("eumpa-studio:selected-project-id", "project-1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Persisted Project" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run alignment" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add manual shot" })).toBeInTheDocument();
    expect(screen.getByText("Use alignment for a lyric-based pass, or add a manual shot when you want to block scenes yourself.")).toBeInTheDocument();

    const pendingJob = await screen.findByLabelText("Pending job: align project-1");
    expect(pendingJob).toHaveTextContent("align");
    expect(pendingJob).toHaveTextContent("project-1");
  });
});
