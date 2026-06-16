import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { Asset, Attempt, ExecutionMode, Job, Shot, WorkflowTemplate } from "../api/types";
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

const configuredAttempt: Attempt = {
  ...attempt,
  workflow_template_id: "template-1",
  execution_mode_id: "mode-1",
  prompt_ko: "한국어 프롬프트",
  prompt_en: "English prompt",
};

const template: WorkflowTemplate = {
  id: "template-1",
  name: "LTX image to video",
  json_path: "workflow.json",
  file_hash: null,
  version: null,
  compatibility_notes: null,
  is_available: true,
  validation_error: null,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
};

const mode: ExecutionMode = {
  id: "mode-1",
  workflow_template_id: "template-1",
  name: "Image prompt",
  required_inputs: '["image", "prompt_en"]',
  optional_inputs: null,
  node_bindings: "{}",
  validation_rules: null,
  exposed_params: null,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
};

const renderJob: Job = {
  id: "job-1",
  type: "render",
  target_entity_type: "attempt",
  target_entity_id: "attempt-1",
  status: "Pending",
  logs: null,
  error: null,
  created_at: "2026-06-16T00:00:00Z",
  updated_at: "2026-06-16T00:00:00Z",
  started_at: null,
  finished_at: null,
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
    if (url === "/api/workflows/templates") {
      return Promise.resolve(jsonResponse([template]));
    }
    if (url === "/api/workflows/templates/template-1/modes") {
      return Promise.resolve(jsonResponse([mode]));
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
    if (
      url === "/api/shots/shot-1/attempts/attempt-1" &&
      init?.method === "PATCH"
    ) {
      return Promise.resolve(jsonResponse(configuredAttempt));
    }
    if (
      url === "/api/shots/shot-1/attempts/attempt-1/render" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(jsonResponse(renderJob, { status: 201 }));
    }
    if (
      url === "/api/shots/shot-1/attempts/attempt-1/review" &&
      init?.method === "POST"
    ) {
      return Promise.resolve(jsonResponse({ ...configuredAttempt, status: "Redo" }));
    }
    if (
      url === "/api/shots/shot-1/attempts/attempt-1" &&
      init?.method === "DELETE"
    ) {
      return Promise.resolve(new Response(null, { status: 204 }));
    }

    return Promise.reject(new Error(`Unhandled request: ${url}`));
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ShotDrawer asset attempts", () => {
  test("separates reference image selection from explicit attempt creation", async () => {
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
    expect(
      await screen.findByRole("button", { name: "Select asset reference.png" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Select asset reference.png" }));

    expect(screen.getByText("No attempts yet.")).toBeInTheDocument();
    expect(onShotUpdated).not.toHaveBeenCalled();
    expect(window.fetch).not.toHaveBeenCalledWith(
      "/api/assets/project-1/asset-1/use-for-shot/shot-1",
      expect.anything(),
    );

    await user.click(
      await screen.findByRole("button", { name: "Create attempt from reference.png" }),
    );

    await waitFor(() => expect(screen.getAllByText("No prompt").length).toBeGreaterThan(0));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate Prompt" })).toBeEnabled();
      expect(onShotUpdated).toHaveBeenCalled();
    });
    await user.click(screen.getByRole("button", { name: "Expand Review" }));
    expect(screen.getByRole("button", { name: "Play Video" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Review Note" })).toBeEnabled();

    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Workflow Template" }),
      "template-1",
    );
    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Execution Mode" }),
      "mode-1",
    );
    await user.click(screen.getByRole("button", { name: "Save Render Setup" }));
    await user.click(
      await screen.findByRole("button", { name: "Queue render for active attempt" }),
    );

    expect(await screen.findByText("Render job queued")).toBeInTheDocument();
  });

  test("shows one editable prompt surface for the active attempt", async () => {
    vi.mocked(window.fetch).mockImplementation((input) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([configuredAttempt]));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([asset]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }
      if (url === "/api/workflows/templates/template-1/modes") {
        return Promise.resolve(jsonResponse([mode]));
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: configuredAttempt,
          attempt_count: 1,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    expect(await screen.findByRole("textbox", { name: "Korean prompt" })).toHaveValue(
      "한국어 프롬프트",
    );
    expect(screen.getByRole("textbox", { name: "English prompt" })).toHaveValue(
      "English prompt",
    );
    expect(screen.queryByRole("textbox", { name: "Prompt KO" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Prompt EN" })).not.toBeInTheDocument();
  });

  test("shows a shot audio segment preview", async () => {
    render(
      <ShotDrawer
        shot={shot}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    const audio = await screen.findByLabelText("Audio preview for 0-5s");

    expect(audio).toHaveAttribute("src", "/api/projects/project-1/audio#t=0,5");
  });

  test("shows API detail when render queue validation fails", async () => {
    const user = userEvent.setup();
    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([configuredAttempt]));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }
      if (url === "/api/workflows/templates/template-1/modes") {
        return Promise.resolve(jsonResponse([mode]));
      }
      if (url === "/api/shots/shot-1" && init?.method === "PATCH") {
        return Promise.resolve(
          jsonResponse({
            ...shot,
            active_attempt_id: "attempt-1",
            active_attempt: configuredAttempt,
            attempt_count: 1,
          }),
        );
      }
      if (
        url === "/api/shots/shot-1/attempts/attempt-1/render" &&
        init?.method === "POST"
      ) {
        return Promise.resolve(
          jsonResponse(
            { detail: "Workflow template file not found: /tmp/missing.json" },
            { status: 422, statusText: "Unprocessable Entity" },
          ),
        );
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: configuredAttempt,
          attempt_count: 1,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    await screen.findAllByText("한국어 프롬프트");
    await user.click(
      await screen.findByRole("button", { name: "Queue render for active attempt" }),
    );

    expect(
      await screen.findByText("Workflow template file not found: /tmp/missing.json"),
    ).toBeInTheDocument();
  });

  test("keeps primary render action visible when render settings are collapsed", async () => {
    const user = userEvent.setup();
    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([configuredAttempt]));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([asset]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }
      if (url === "/api/workflows/templates/template-1/modes") {
        return Promise.resolve(jsonResponse([mode]));
      }
      if (
        url === "/api/shots/shot-1/attempts/attempt-1/render" &&
        init?.method === "POST"
      ) {
        return Promise.resolve(jsonResponse(renderJob, { status: 201 }));
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: configuredAttempt,
          attempt_count: 1,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    await user.click(await screen.findByRole("button", { name: "Collapse Render settings" }));

    expect(screen.queryByRole("combobox", { name: "Workflow Template" })).not.toBeInTheDocument();

    const primaryRenderButton = screen.getByRole("button", {
      name: "Queue render for active attempt",
    });
    expect(primaryRenderButton).toBeEnabled();

    await user.click(primaryRenderButton);

    expect(await screen.findByText("Render job queued")).toBeInTheDocument();
  });

  test("explains why render cannot be queued", async () => {
    vi.mocked(window.fetch).mockImplementation((input) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([attempt]));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([asset]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: attempt,
          attempt_count: 1,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    expect(await screen.findByText("Choose a workflow and mode before rendering.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Queue render for active attempt" }),
    ).toBeDisabled();
  });

  test("shows explicit attempt card actions and deletes an attempt", async () => {
    const user = userEvent.setup();
    const onShotUpdated = vi.fn();
    const secondAttempt: Attempt = {
      ...attempt,
      id: "attempt-2",
      status: "Rejected",
      prompt_ko: "삭제할 프롬프트",
      created_at: "2026-06-16T02:00:00Z",
    };

    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([configuredAttempt, secondAttempt]));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([asset]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }
      if (url === "/api/workflows/templates/template-1/modes") {
        return Promise.resolve(jsonResponse([mode]));
      }
      if (url === "/api/shots/shot-1" && init?.method === "PATCH") {
        return Promise.resolve(
          jsonResponse({
            ...shot,
            active_attempt_id: "attempt-2",
            active_attempt: secondAttempt,
            attempt_count: 2,
          }),
        );
      }
      if (
        url === "/api/shots/shot-1/attempts/attempt-2" &&
        init?.method === "DELETE"
      ) {
        return Promise.resolve(new Response(null, { status: 204 }));
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-1",
          active_attempt: configuredAttempt,
          attempt_count: 2,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={onShotUpdated}
      />,
    );

    expect(await screen.findByText("Active attempt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use attempt attempt-2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete attempt attempt-2" })).toBeInTheDocument();
    expect(screen.getAllByText("Ready to render").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Use attempt attempt-2" }));
    await waitFor(() => expect(onShotUpdated).toHaveBeenCalled());

    await user.click(screen.getByRole("button", { name: "Delete attempt attempt-2" }));

    await waitFor(() => {
      expect(screen.queryByText("삭제할 프롬프트")).not.toBeInTheDocument();
    });
    expect(window.fetch).toHaveBeenCalledWith(
      "/api/shots/shot-1/attempts/attempt-2",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
