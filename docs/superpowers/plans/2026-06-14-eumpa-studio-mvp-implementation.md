# eumpa_studio MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable `eumpa_studio` MVP: a FastAPI + React internal web app that creates shot-based production projects, generates prompts through Codex CLI, queues ComfyUI renders, reviews candidates, and exports selected clips.

**Architecture:** Use a Python FastAPI backend as the source of truth for metadata, files, execution jobs, and ComfyUI/Codex integration. Use a React frontend for the shot production table, right drawer, asset picker, queue panel, and review/export controls. Store metadata in SQLite with migration-ready models, keep heavy render outputs on the ComfyUI server, and access them through ComfyUI output metadata and `/view`.

**Tech Stack:** Python, FastAPI, SQLAlchemy 2, Alembic, SQLite, pytest, React, TypeScript, Vite, TanStack Query, TanStack Table, custom drawer/modal components, Codex CLI, ComfyUI HTTP API.

---

## Linear Tracking

Project: [eumpa_studio MVP](https://linear.app/eprp/project/eumpa-studio-mvp-269776f6c972)

Milestones:

- `1. App Foundation`
- `2. Project, Shot, and Asset Workspace`
- `3. Prompt Generation`
- `4. ComfyUI Render Pipeline`
- `5. Review and Export`

Issues:

- `EPR-5` Scaffold FastAPI + React workspace
- `EPR-6` Add SQLite schema and migrations for MVP entities
- `EPR-7` Implement configuration and service health checks
- `EPR-8` Build project creation with audio, lyrics, visual bible, and assets
- `EPR-9` Implement audio alignment job and draft shot generation
- `EPR-10` Build shot production table UI
- `EPR-11` Build right drawer for shot editing and attempt review
- `EPR-12` Add simple asset picker and upload flow
- `EPR-13` Implement workflow template and execution mode registry
- `EPR-14` Implement Codex CLI prompt generation provider
- `EPR-15` Add prompt generation UI and prompt editing
- `EPR-16` Implement DB-backed job queue and single worker
- `EPR-17` Implement ComfyUI render submission and result metadata
- `EPR-18` Implement candidate playback and review status actions
- `EPR-19` Export selected clips and metadata
- `EPR-20` Add one-command start and MVP operator docs

## File Structure

Create this structure unless implementation discovers a strong reason to adjust it:

```text
apps/
  web/
    package.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      api/client.ts
      api/types.ts
      components/
        AppShell.tsx
        HealthBar.tsx
        ProjectChooser.tsx
        ShotTable.tsx
        ShotDrawer.tsx
        AssetPicker.tsx
        QueuePanel.tsx
        VideoPreviewModal.tsx
      hooks/
        useHealth.ts
        useProjects.ts
        useShots.ts
        useJobs.ts
      styles/
        app.css
src/
  eumpa_studio/
    __init__.py
    cli.py
    config.py
    server/
      app.py
      deps.py
      routes/
        assets.py
        export.py
        health.py
        jobs.py
        projects.py
        prompts.py
        shots.py
        workflows.py
    domain/
      models.py
      statuses.py
    db/
      base.py
      session.py
      migrations/
    storage/
      paths.py
      media.py
    execution/
      align.py
      codex_prompt.py
      comfy_client.py
      jobs.py
      worker.py
      workflow_patch.py
    export/
      selected.py
tests/
  backend/
    test_models.py
    test_projects.py
    test_alignment.py
    test_codex_prompt.py
    test_workflow_patch.py
    test_jobs.py
    test_export.py
docs/
  operations/
    local-start.md
    server-topology.md
```

Responsibilities:

- `domain/`: stable data names, status enums, and Pydantic/domain models shared across routes and execution.
- `db/`: database engine/session/migrations and ORM models.
- `storage/`: managed project paths, relative path handling, thumbnails/proxies, and uploaded files.
- `execution/`: long-running job implementations and external integrations.
- `server/routes/`: thin HTTP endpoints that validate inputs and call domain/execution services.
- `apps/web/src/components/`: user-facing workflow UI.

## Task Plan

### Task 1: Scaffold App Foundation (`EPR-5`)

**Files:**

- Create: `pyproject.toml`
- Create: `src/eumpa_studio/cli.py`
- Create: `src/eumpa_studio/server/app.py`
- Create: `apps/web/package.json`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/main.tsx`
- Create: `docs/operations/local-start.md`

- [ ] Create backend package with a FastAPI app exposing `GET /api/health`.
- [ ] Create Vite React app with an app shell that fetches `/api/health`.
- [ ] Add backend test for health endpoint.
- [ ] Add frontend typecheck/build command.
- [ ] Run `uv run pytest tests/backend -q`.
- [ ] Run `cd apps/web && pnpm build`.
- [ ] Commit: `feat: scaffold eumpa studio app`

### Task 2: Add SQLite Schema and Migrations (`EPR-6`)

**Files:**

- Create: `src/eumpa_studio/domain/statuses.py`
- Create: `src/eumpa_studio/db/base.py`
- Create: `src/eumpa_studio/db/session.py`
- Create: `src/eumpa_studio/domain/models.py`
- Create: `tests/backend/test_models.py`

- [ ] Define status enums exactly matching the design spec: `Needs Input`, `Ready`, `Queued`, `Rendering`, `Needs Review`, `Selected`, `Redo`, `Rejected`, `Failed`.
- [ ] Add ORM models for Project, Shot, Attempt, Asset, WorkflowTemplate, ExecutionMode, and Job.
- [ ] Store file references as `storage_backend`, `relative_path`, and optional resolved path fields.
- [ ] Write tests that create a project, shot, attempt, asset, workflow template, execution mode, and job.
- [ ] Run `uv run pytest tests/backend/test_models.py -q`.
- [ ] Commit: `feat: add mvp metadata schema`

### Task 3: Add Configuration and Health Checks (`EPR-7`)

**Files:**

- Create: `src/eumpa_studio/config.py`
- Create: `src/eumpa_studio/server/routes/health.py`
- Create: `apps/web/src/components/HealthBar.tsx`
- Create: `apps/web/src/hooks/useHealth.ts`
- Test: `tests/backend/test_health.py`

- [ ] Implement config loading for data root, ComfyUI URL, Codex CLI path, alignment command/settings, output path, and cache path.
- [ ] Health route returns backend, database, ComfyUI reachability, and Codex CLI availability.
- [ ] HealthBar displays each health item without blocking the rest of the app.
- [ ] Tests cover healthy and unavailable external services with mocked calls.
- [ ] Run backend tests and frontend build.
- [ ] Commit: `feat: add service health checks`

### Task 4: Implement Project Creation (`EPR-8`)

**Files:**

- Create: `src/eumpa_studio/storage/paths.py`
- Create: `src/eumpa_studio/server/routes/projects.py`
- Create: `apps/web/src/components/ProjectChooser.tsx`
- Create: `apps/web/src/hooks/useProjects.ts`
- Test: `tests/backend/test_projects.py`

- [ ] Add project creation API accepting project name, audio upload, lyrics text/file, visual bible text/file, and asset uploads/folder reference.
- [ ] Snapshot project inputs into managed storage under the configured data root.
- [ ] Return project detail with input metadata and default settings.
- [ ] Build ProjectChooser UI for create/open project.
- [ ] Tests verify project input snapshot paths and project retrieval.
- [ ] Commit: `feat: add project creation`

### Task 5: Implement Alignment and Draft Shots (`EPR-9`)

**Files:**

- Create: `src/eumpa_studio/execution/align.py`
- Modify: `src/eumpa_studio/server/routes/jobs.py`
- Test: `tests/backend/test_alignment.py`

- [ ] Add an alignment job type that runs the configured alignment command or adapter.
- [ ] Parse alignment output into start/end/duration, speaker, and lyrics text.
- [ ] Create draft Shot rows in shot order.
- [ ] Preserve existing shots if an alignment job fails.
- [ ] Tests cover parsing, shot creation, and failure handling.
- [ ] Commit: `feat: generate draft shots from alignment`

### Task 6: Build Shot Production Table (`EPR-10`)

**Files:**

- Create: `src/eumpa_studio/server/routes/shots.py`
- Create: `apps/web/src/components/ShotTable.tsx`
- Create: `apps/web/src/hooks/useShots.ts`
- Modify: `apps/web/src/App.tsx`

- [ ] Add API to list shots with active attempt details.
- [ ] Render table columns from the design spec.
- [ ] Implement row-level attempt selector that changes image, prompt, and render preview as a linked set.
- [ ] Add shot-range audio play button.
- [ ] Handle empty projects and shots with no attempts.
- [ ] Commit: `feat: add shot production table`

### Task 7: Build Right Drawer (`EPR-11`)

**Files:**

- Create: `apps/web/src/components/ShotDrawer.tsx`
- Modify: `src/eumpa_studio/server/routes/shots.py`
- Test: `tests/backend/test_shots.py`

- [ ] Add API endpoints for updating shot time range, shot note, active attempt, and review note.
- [ ] Drawer displays full lyrics, shot note editor, audio repeat preview, full prompt KO/EN, attempt list, and rendered video area.
- [ ] Drawer exposes status actions without deleting attempts.
- [ ] Tests verify shot updates and active attempt behavior.
- [ ] Commit: `feat: add shot drawer editing`

### Task 8: Add Asset Picker (`EPR-12`)

**Files:**

- Create: `src/eumpa_studio/server/routes/assets.py`
- Create: `src/eumpa_studio/storage/media.py`
- Create: `apps/web/src/components/AssetPicker.tsx`
- Test: `tests/backend/test_assets.py`

- [ ] List project image assets with thumbnail URLs.
- [ ] Support browser upload into project assets.
- [ ] Selecting a new image creates a new attempt draft and leaves previous attempts intact.
- [ ] Tests verify upload, list, and attempt draft creation.
- [ ] Commit: `feat: add simple asset picker`

### Task 9: Add Workflow Template and Execution Mode Registry (`EPR-13`)

**Files:**

- Create: `src/eumpa_studio/execution/workflow_patch.py`
- Create: `src/eumpa_studio/server/routes/workflows.py`
- Test: `tests/backend/test_workflow_patch.py`

- [ ] Store WorkflowTemplate with name, JSON path, hash/version, and compatibility note.
- [ ] Store ExecutionMode with required inputs, node bindings, validation rules, and exposed basic params.
- [ ] Implement workflow patching for selected image/audio/prompt/params.
- [ ] Save patched workflow JSON snapshot on attempt before render submission.
- [ ] Tests verify binding validation and patch output.
- [ ] Commit: `feat: add workflow mode registry`

### Task 10: Implement Codex CLI Prompt Provider (`EPR-14`)

**Files:**

- Create: `src/eumpa_studio/execution/codex_prompt.py`
- Create: `src/eumpa_studio/server/routes/prompts.py`
- Test: `tests/backend/test_codex_prompt.py`

- [ ] Build Codex prompt context from visual bible, lyrics, speaker, shot note, time range, prior attempt context, and LTX rules.
- [ ] Invoke Codex CLI with selected image as an image input.
- [ ] Require structured JSON output fields: image observations, motion/camera plan, prompt KO, prompt EN, negative rules, and rationale.
- [ ] Store generated prompt on an attempt draft.
- [ ] Tests mock subprocess success, timeout, nonzero exit, invalid JSON, and missing CLI.
- [ ] Commit: `feat: add codex prompt provider`

### Task 11: Add Prompt UI (`EPR-15`)

**Files:**

- Modify: `apps/web/src/components/ShotDrawer.tsx`
- Modify: `apps/web/src/api/client.ts`

- [ ] Add Generate Prompt action in drawer.
- [ ] Show prompt job state while Codex runs.
- [ ] Display prompt KO and prompt EN in full editable fields.
- [ ] Save edited prompts before rendering.
- [ ] Commit: `feat: add prompt generation UI`

### Task 12: Add DB-Backed Job Queue (`EPR-16`)

**Files:**

- Create: `src/eumpa_studio/execution/jobs.py`
- Create: `src/eumpa_studio/execution/worker.py`
- Create: `src/eumpa_studio/server/routes/jobs.py`
- Create: `apps/web/src/components/QueuePanel.tsx`
- Create: `apps/web/src/hooks/useJobs.ts`
- Test: `tests/backend/test_jobs.py`

- [ ] Persist jobs in SQLite with type, target entity, status, logs, error, and timestamps.
- [ ] Implement worker loop that runs one job at a time.
- [ ] Continue to next job after failure.
- [ ] Add queue panel showing current job and pending jobs.
- [ ] Tests verify sequential execution and failure continuation.
- [ ] Commit: `feat: add persistent job queue`

### Task 13: Implement ComfyUI Render Submission (`EPR-17`)

**Files:**

- Create: `src/eumpa_studio/execution/comfy_client.py`
- Modify: `src/eumpa_studio/execution/worker.py`
- Test: `tests/backend/test_comfy_render.py`

- [ ] Validate required inputs for attempt execution mode.
- [ ] Patch workflow JSON and save the snapshot.
- [ ] Submit to ComfyUI API and store prompt id.
- [ ] Poll history for outputs.
- [ ] Store filename, subfolder, type, server id, and `/view` preview metadata.
- [ ] Set attempt to `Needs Review` on success and `Failed` on failure.
- [ ] Commit: `feat: submit renders to comfyui`

### Task 14: Add Candidate Playback and Review (`EPR-18`)

**Files:**

- Create: `apps/web/src/components/VideoPreviewModal.tsx`
- Modify: `apps/web/src/components/ShotDrawer.tsx`
- Modify: `src/eumpa_studio/server/routes/shots.py`

- [ ] Play candidate videos through ComfyUI output access.
- [ ] Add large preview modal.
- [ ] Add Selected, Redo, Rejected, and Failed status actions.
- [ ] Save review notes per attempt.
- [ ] Ensure selecting an attempt updates shot active/selected state without deleting other attempts.
- [ ] Commit: `feat: add candidate review`

### Task 15: Export Selected Clips (`EPR-19`)

**Files:**

- Create: `src/eumpa_studio/export/selected.py`
- Create: `src/eumpa_studio/server/routes/export.py`
- Test: `tests/backend/test_export.py`

- [ ] Collect selected attempts in shot order.
- [ ] Copy or link selected clips into project export storage.
- [ ] Write shot list CSV or JSON.
- [ ] Write attempt snapshot JSON with prompt, seed, workflow template/mode, params, and output metadata.
- [ ] Tests verify output ordering and metadata content.
- [ ] Commit: `feat: export selected clips`

### Task 16: Add One-Command Start and Operator Docs (`EPR-20`)

**Files:**

- Modify: `src/eumpa_studio/cli.py`
- Create: `docs/operations/server-topology.md`
- Modify: `docs/operations/local-start.md`

- [ ] Add `eumpa_studio start` command that starts backend, static frontend serving, DB, and worker.
- [ ] Document required config for data root, ComfyUI URL, Codex CLI path, and output/cache paths.
- [ ] Document small-server / large-ComfyUI-server topology.
- [ ] Document startup health troubleshooting.
- [ ] Run full backend tests and frontend build.
- [ ] Commit: `docs: add mvp operator guide`

## Verification Before MVP Complete

- [ ] `uv run pytest tests/backend -q` passes.
- [ ] `cd apps/web && pnpm build` passes.
- [ ] Create a sample project.
- [ ] Run alignment and confirm draft shots appear.
- [ ] Pick an image for a shot and confirm a new attempt draft is created.
- [ ] Generate a Codex prompt with image input.
- [ ] Queue a mocked or live ComfyUI render.
- [ ] Preview the candidate video.
- [ ] Mark a candidate selected.
- [ ] Export selected clips and metadata.

## Scope Notes

The MVP is large enough that implementation should proceed milestone by milestone. The first independently testable release is Milestone 1 plus enough of Milestone 2 to create a project and list empty shots. Do not start ComfyUI or Codex integration before the schema, config, storage, and job queue foundations are stable.
