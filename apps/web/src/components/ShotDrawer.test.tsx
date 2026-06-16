import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Asset, Attempt, Shot } from "../api/types";
import { ShotDrawer } from "./ShotDrawer";

const shot: Shot = {
  id: "shot-1",
  project_id: "project-1",
  order: 0,
  start_time: 0,
  end_time: 5,
  duration: 5,
  speaker: null,
  lyrics_text: "sample lyric",
  shot_note: "wide stage",
  status: "Needs Input",
  active_attempt_id: null,
  active_attempt: null,
  attempt_count: 0,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
};

const asset: Asset = {
  id: "asset-1",
  project_id: "project-1",
  name: "reference.png",
  storage_backend: "local",
  relative_path: "assets/reference.png",
  mime_type: "image/png",
  created_at: "2026-06-16T00:00:00Z",
  url: "/api/assets/project-1/asset-1",
  thumb_url: "/api/assets/project-1/asset-1/thumb",
};

const attempt: Attempt = {
  id: "attempt-1",
  shot_id: "shot-1",
  parent_attempt_id: null,
  image_storage_backend: "local",
  image_relative_path: "assets/reference.png",
  end_image_storage_backend: null,
  end_image_relative_path: null,
  input_video_storage_backend: null,
  input_video_relative_path: null,
  shot_note_snapshot: null,
  prompt_ko: null,
  prompt_en: null,
  workflow_template_id: null,
  execution_mode_id: null,
  param_overrides: null,
  seed: null,
  workflow_snapshot: null,
  comfyui_prompt_id: null,
  output_metadata: null,
  review_note: null,
  status: "Needs Input",
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
  vi.spyOn(window, "fetch").mockImplementation((input, init) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url === "/api/shots/shot-1/attempts") {
      return Promise.resolve(jsonResponse([]));
    }
    if (url === "/api/assets/project-1") {
      return Promise.resolve(jsonResponse([asset]));
    }
    if (
      url === "/api/assets/project-1/asset-1/use-for-shot/shot-1" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(jsonResponse(attempt, { status: 201 }));
    }
    if (url === "/api/shots/shot-1" && init?.method === "PATCH") {
      return Promise.resolve(
        jsonResponse({
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: attempt,
          attempt_count: 1,
        }),
      );
    }

    return Promise.reject(new Error(`Unhandled request: ${url}`));
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ShotDrawer asset attempts", () => {
  test("lets the user create and activate an attempt from a project asset", async () => {
    const user = userEvent.setup();
    const onShotUpdated = vi.fn();

    render(
      <ShotDrawer
        shot={shot}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={onShotUpdated}
      />,
    );

    expect(await screen.findByText("No attempts yet.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Use asset reference.png" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Use asset reference.png" }));

    expect(await screen.findByText("No prompt")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate Prompt" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "Play Video" })).toBeEnabled();
      expect(screen.getByRole("textbox", { name: "Review Note" })).toBeEnabled();
      expect(onShotUpdated).toHaveBeenCalled();
    });
  });
});
