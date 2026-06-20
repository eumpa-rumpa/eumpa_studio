import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Shot } from "../api/types";
import { ShotTable } from "./ShotTable";

const renderedShot: Shot = {
  id: "shot-1",
  project_id: "project-1",
  order: 0,
  start_time: 0,
  end_time: 4.2,
  duration: 4.2,
  speaker: "Vocal",
  lyrics_text: "첫 번째 라인의 보컬과 카메라 무빙을 확인한다",
  shot_note: "Stage turn before chorus drop",
  status: "Needs Review",
  active_attempt_id: "attempt-1",
  active_attempt: {
    id: "attempt-1",
    status: "Needs Review",
    image_storage_backend: null,
    image_relative_path: "references/reference.png",
    prompt_ko: "카메라가 보컬을 따라가며 조명 전환을 강조한다",
    prompt_en: null,
    output_metadata: '{"filename":"output.mp4"}',
    video_url: "http://localhost:8188/view?filename=output.mp4&subfolder=&type=output",
  },
  attempt_count: 3,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
};

const emptyShot: Shot = {
  id: "shot-2",
  project_id: "project-1",
  order: 1,
  start_time: 4.2,
  end_time: 8,
  duration: 3.8,
  speaker: null,
  lyrics_text: "두 번째 라인",
  shot_note: null,
  status: "Needs Input",
  active_attempt_id: null,
  active_attempt: null,
  attempt_count: 0,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
};

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

beforeEach(() => {
  vi.spyOn(window, "fetch").mockImplementation((input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url === "/api/shots?project_id=project-1") {
      return Promise.resolve(jsonResponse([renderedShot, emptyShot]));
    }

    return Promise.reject(new Error(`Unhandled request: ${url}`));
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ShotTable", () => {
  test("keeps compact planning and active attempt context visible in the table", async () => {
    render(<ShotTable projectId="project-1" />);

    expect(await screen.findByRole("columnheader", { name: "Note" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Attempt" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Image" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Prompt" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Render" })).not.toBeInTheDocument();

    expect(screen.getByText("Stage turn before chorus drop")).toBeInTheDocument();
    expect(screen.getByText("Active / 3")).toBeInTheDocument();
    expect(screen.getByText("reference.png")).toBeInTheDocument();
    expect(screen.getByText("카메라가 보컬을 따라가며 조명 전환을 강조한다")).toBeInTheDocument();

    const preview = screen.getByLabelText("Video preview for shot 1");
    expect(preview).toBeInTheDocument();
    expect(preview).toHaveAttribute(
      "src",
      "http://localhost:8188/view?filename=output.mp4&subfolder=&type=output",
    );
  });

  test("shows empty attempt states while keeping row actions reachable", async () => {
    render(<ShotTable projectId="project-1" />);

    expect(await screen.findByText("0 attempts")).toBeInTheDocument();
    expect(screen.getByText("No image")).toBeInTheDocument();
    expect(screen.getByText("No prompt")).toBeInTheDocument();
    expect(screen.getByText("No render")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open" })).toHaveLength(2);
  });
});
