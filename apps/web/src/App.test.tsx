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

const jobs: Job[] = [];
const shots: Shot[] = [];

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

beforeEach(() => {
  localStorage.clear();
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
});
