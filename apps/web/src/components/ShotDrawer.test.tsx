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

const renderedAttempt: Attempt = {
  ...configuredAttempt,
  id: "attempt-rendered",
  status: "Needs Review",
  output_metadata: '{"filename":"output.mp4","subfolder":"","type":"output"}',
  review_note: "looks good",
  created_at: "2026-06-16T01:00:00Z",
  updated_at: "2026-06-16T01:00:00Z",
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
  test("creates an attempt explicitly before assigning a reference image", async () => {
    const user = userEvent.setup();
    const onShotUpdated = vi.fn();

    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts" && init?.method !== "POST") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/shots/shot-1/attempts" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(attempt, { status: 201 }));
      }
      if (url === "/api/assets/project-1") {
        return Promise.resolve(jsonResponse([asset]));
      }
      if (url === "/api/workflows/templates") {
        return Promise.resolve(jsonResponse([template]));
      }
      if (
        url === "/api/shots/shot-1/attempts/attempt-1" &&
        init?.method === "PATCH"
      ) {
        return Promise.resolve(
          jsonResponse({
            ...attempt,
            image_storage_backend: asset.storage_backend,
            image_relative_path: asset.relative_path,
          }),
        );
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={shot}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={onShotUpdated}
      />,
    );

    expect(await screen.findByText("No attempts yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Select asset reference.png" })).not.toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: "New attempt" }));
    await user.click(
      await screen.findByRole("button", {
        name: "Select start image reference.png for attempt attempt-1",
      }),
    );

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/api/shots/shot-1/attempts/attempt-1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            image_storage_backend: "local",
            image_relative_path: "assets/reference.png",
          }),
        }),
      );
    });
    expect(window.fetch).not.toHaveBeenCalledWith(
      "/api/assets/project-1/asset-1/use-for-shot/shot-1",
      expect.anything(),
    );
    expect(onShotUpdated).toHaveBeenCalled();
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

    expect(await screen.findByRole("textbox", { name: "Korean prompt for attempt attempt-1" })).toHaveValue(
      "한국어 프롬프트",
    );
    expect(screen.getByRole("textbox", { name: "English prompt for attempt attempt-1" })).toHaveValue(
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
      await screen.findByRole("button", { name: "Queue render for attempt attempt-1" }),
    );

    expect(
      await screen.findByText("Workflow template file not found: /tmp/missing.json"),
    ).toBeInTheDocument();
  });

  test("keeps render action inside the expanded attempt", async () => {
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

    const primaryRenderButton = await screen.findByRole("button", {
      name: "Queue render for attempt attempt-1",
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
      screen.getByRole("button", { name: "Queue render for attempt attempt-1" }),
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

  test("creates a new attempt and opens attempt-owned controls", async () => {
    const user = userEvent.setup();
    const onShotUpdated = vi.fn();

    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts" && init?.method !== "POST") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/shots/shot-1/attempts" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(attempt, { status: 201 }));
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
        shot={shot}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={onShotUpdated}
      />,
    );

    await user.click(await screen.findByRole("button", { name: "New attempt" }));

    expect(
      await screen.findByRole("button", { name: "Collapse attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select start image reference.png for attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Select end image reference.png for attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Shot note for prompt for attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Korean prompt for attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: "Workflow Template for attempt attempt-1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Queue render for attempt attempt-1" }),
    ).toBeDisabled();
    expect(onShotUpdated).toHaveBeenCalled();
  });

  test("lets users fully collapse attempts after defaulting to the latest attempt", async () => {
    const user = userEvent.setup();
    const olderAttempt: Attempt = {
      ...attempt,
      id: "attempt-older",
      prompt_en: "Older prompt",
      created_at: "2026-06-16T01:00:00Z",
    };
    const latestAttempt: Attempt = {
      ...configuredAttempt,
      id: "attempt-latest",
      prompt_en: "Latest prompt",
      created_at: "2026-06-16T02:00:00Z",
    };

    vi.mocked(window.fetch).mockImplementation((input) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([olderAttempt, latestAttempt]));
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
        shot={{ ...shot, attempt_count: 2 }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    const latestToggle = await screen.findByRole("button", {
      name: "Collapse attempt attempt-latest",
    });
    expect(screen.getByRole("textbox", { name: "English prompt for attempt attempt-latest" })).toHaveValue(
      "Latest prompt",
    );

    await user.click(latestToggle);

    expect(
      screen.getByRole("button", { name: "Expand attempt attempt-latest" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "English prompt for attempt attempt-latest" }),
    ).not.toBeInTheDocument();
  });

  test("selecting start and optional end images updates separate attempt fields", async () => {
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
        url === "/api/shots/shot-1/attempts/attempt-1" &&
        init?.method === "PATCH"
      ) {
        const body = JSON.parse(String(init.body ?? "{}")) as Partial<Attempt>;
        return Promise.resolve(
          jsonResponse({
            ...configuredAttempt,
            ...body,
          }),
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

    await user.click(
      await screen.findByRole("button", {
        name: "Select start image reference.png for attempt attempt-1",
      }),
    );

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/api/shots/shot-1/attempts/attempt-1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            image_storage_backend: "local",
            image_relative_path: "assets/reference.png",
          }),
        }),
      );
    });
    await user.click(
      screen.getByRole("button", {
        name: "Select end image reference.png for attempt attempt-1",
      }),
    );
    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/api/shots/shot-1/attempts/attempt-1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            end_image_storage_backend: "local",
            end_image_relative_path: "assets/reference.png",
          }),
        }),
      );
    });
    await user.click(screen.getByRole("button", { name: "Clear end image for attempt attempt-1" }));
    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/api/shots/shot-1/attempts/attempt-1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            end_image_storage_backend: null,
            end_image_relative_path: null,
          }),
        }),
      );
    });
    expect(window.fetch).not.toHaveBeenCalledWith(
      "/api/assets/project-1/asset-1/use-for-shot/shot-1",
      expect.anything(),
    );
  });

  test("sends shot note and editable system prompt when generating a prompt", async () => {
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
        url === "/api/shots/shot-1/attempts/attempt-1" &&
        init?.method === "PATCH"
      ) {
        const body = JSON.parse(String(init.body ?? "{}")) as Partial<Attempt>;
        return Promise.resolve(jsonResponse({ ...configuredAttempt, ...body }));
      }
      if (url === "/api/prompts/generate" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({
            ...configuredAttempt,
            shot_note_snapshot: "인물이 신나게 손을 펼치며 랩을 한다",
            prompt_ko: "생성된 한국어 프롬프트",
            prompt_en: "Generated English prompt",
          }),
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

    await user.clear(
      await screen.findByRole("textbox", { name: "Shot note for prompt for attempt attempt-1" }),
    );
    await user.type(
      screen.getByRole("textbox", { name: "Shot note for prompt for attempt attempt-1" }),
      "인물이 신나게 손을 펼치며 랩을 한다",
    );
    await user.click(screen.getByRole("button", { name: "Edit system prompt for attempt attempt-1" }));
    await user.clear(screen.getByRole("textbox", { name: "System prompt for attempt attempt-1" }));
    await user.type(
      screen.getByRole("textbox", { name: "System prompt for attempt attempt-1" }),
      "Custom LTX direction",
    );
    await user.click(screen.getByRole("button", { name: "Generate prompt for attempt attempt-1" }));

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/api/shots/shot-1/attempts/attempt-1",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            shot_note_snapshot: "인물이 신나게 손을 펼치며 랩을 한다",
            prompt_ko: "한국어 프롬프트",
            prompt_en: "English prompt",
          }),
        }),
      );
    });
    expect(window.fetch).toHaveBeenCalledWith(
      "/api/prompts/generate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          attempt_id: "attempt-1",
          system_prompt: "Custom LTX direction",
        }),
      }),
    );
    expect(await screen.findByDisplayValue("Generated English prompt")).toBeInTheDocument();
  });

  test("rendered attempt inputs are locked and duplicate creates an editable attempt", async () => {
    const user = userEvent.setup();
    const duplicatedAttempt: Attempt = {
      ...renderedAttempt,
      id: "attempt-copy",
      parent_attempt_id: "attempt-rendered",
      output_metadata: null,
      review_note: null,
      status: "Needs Input",
      created_at: "2026-06-16T02:00:00Z",
      updated_at: "2026-06-16T02:00:00Z",
    };

    vi.mocked(window.fetch).mockImplementation((input, init) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      if (url === "/api/shots/shot-1/attempts") {
        return Promise.resolve(jsonResponse([renderedAttempt]));
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
        url === "/api/shots/shot-1/attempts/attempt-rendered/duplicate" &&
        init?.method === "POST"
      ) {
        return Promise.resolve(jsonResponse(duplicatedAttempt, { status: 201 }));
      }

      return Promise.reject(new Error(`Unhandled request: ${url}`));
    });

    render(
      <ShotDrawer
        shot={{
          ...shot,
          active_attempt_id: "attempt-rendered",
          active_attempt: renderedAttempt,
          attempt_count: 1,
        }}
        projectId="project-1"
        onClose={() => {}}
        onShotUpdated={() => {}}
      />,
    );

    expect(
      await screen.findByRole("textbox", { name: "Korean prompt for attempt attempt-rendered" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Duplicate attempt attempt-rendered" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Duplicate attempt attempt-rendered" }));

    expect(
      await screen.findByRole("button", { name: "Collapse attempt attempt-copy" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Korean prompt for attempt attempt-copy" }),
    ).toBeEnabled();
  });
});
