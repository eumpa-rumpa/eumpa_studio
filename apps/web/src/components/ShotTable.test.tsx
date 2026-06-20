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
  shot_note: "This should not be in the overview table",
  status: "Needs Review",
  active_attempt_id: "attempt-1",
  active_attempt: {
    id: "attempt-1",
    status: "Needs Review",
    image_storage_backend: null,
    image_relative_path: null,
    prompt_ko: null,
    prompt_en: null,
    output_metadata: '{"filename":"output.mp4"}',
    video_url: "http://localhost:8188/view?filename=output.mp4&subfolder=&type=output",
  },
  attempt_count: 1,
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
      return Promise.resolve(jsonResponse([renderedShot]));
    }

    return Promise.reject(new Error(`Unhandled request: ${url}`));
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ShotTable", () => {
  test("replaces shot note with an inline active attempt video preview", async () => {
    render(<ShotTable projectId="project-1" />);

    expect(await screen.findByRole("columnheader", { name: "Preview" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Shot Note" })).not.toBeInTheDocument();
    expect(screen.queryByText("This should not be in the overview table")).not.toBeInTheDocument();

    const preview = screen.getByLabelText("Video preview for shot 1");
    expect(preview).toBeInTheDocument();
    expect(preview).toHaveAttribute(
      "src",
      "http://localhost:8188/view?filename=output.mp4&subfolder=&type=output",
    );
  });
});
