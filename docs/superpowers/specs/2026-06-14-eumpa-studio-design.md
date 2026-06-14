# eumpa_studio Design

Date: 2026-06-14

## Purpose

`eumpa_studio` is an internal AI video production operations tool. It is not a lyrics planning app and does not replace the existing `lyrics` workspace.

The app manages the repeatable production loop for line-by-line or shot-by-shot music video creation:

1. Create a production project from audio, lyrics, visual direction, and image assets.
2. Run audio/lyrics alignment and generate draft shots.
3. Let the user adjust shot rows, time ranges, images, notes, prompts, workflow modes, and render settings.
4. Generate LTX prompts with Codex CLI using the selected image as an image input.
5. Queue ComfyUI render jobs one at a time.
6. Review candidate videos, mark the usable output, and export selected clips.

## Explicit Non-Goals

- Do not automate the `lyrics` planning workflow or depend on the `lyrics/projects` folder structure.
- Do not use Google Drive as the runtime project storage.
- Do not build team permissions, external review links, or multi-user audit workflows for MVP.
- Do not include OpenAI API as a prompt provider in MVP.
- Do not build a ComfyUI graph editor, arbitrary JSON patch editor, or full node-parameter UI in MVP.
- Do not make an Airtable/Baserow/NocoDB-based product. This is a dedicated web app.

## Product Boundary

The production source of truth is the app database plus managed project files. The `lyrics` workspace remains a separate planning/source-notes layer. Users can import or paste text from planning files, but the app stores a production snapshot rather than a live dependency on those files.

Google Drive is used only for final sharing or archive workflows later. MVP export writes selected clips and metadata to an export folder.

## Core Concepts

### Project

A project contains production inputs and defaults:

- project name
- audio file
- lyrics source snapshot
- visual bible snapshot
- asset folder
- default ComfyUI server
- workflow templates and execution modes

### Shot

The primary production unit is a `Shot`, not a lyric line.

A shot can contain part of one lyric line, one full line, or multiple lines. The user can add rows, delete rows, and edit time ranges after automatic alignment.

Shot fields include:

- order
- start time, end time, duration
- speaker
- lyrics text
- shot note
- status
- active attempt

### Attempt

An `Attempt` is a versioned execution snapshot for a shot. Attempts are never silently overwritten.

An attempt includes:

- selected image
- optional end image or input video
- shot note at creation time
- prompt KO
- prompt EN
- workflow template
- execution mode
- basic parameter overrides
- seed
- final patched workflow JSON snapshot
- ComfyUI prompt id
- output metadata
- review note
- status
- parent attempt, when created from a prior attempt

Changing an image, prompt, workflow mode, or render parameter creates a new attempt draft or render attempt. This keeps earlier candidates reproducible.

## Status Model

MVP statuses:

- `Needs Input`
- `Ready`
- `Queued`
- `Rendering`
- `Needs Review`
- `Selected`
- `Redo`
- `Rejected`
- `Failed`

`Redo` is distinct from `Failed`: it means the result rendered but should be tried again for creative reasons.

## User Interface

### Main Layout

The app uses a shot production table with a right-side detail drawer.

The table is for scanning production progress. The drawer is for editing, comparison, and execution.

### Shot Table Columns

MVP table columns:

- `#`
- `time range + play`
- `speaker`
- `lyrics preview`
- `shot note preview`
- `attempt selector`, such as `‹ v2 / 6 ›`
- `image thumbnail`
- `prompt indicator / short preview`
- `render preview thumbnail`
- `status`
- `quick actions`

The table shows the active attempt as a linked set. Moving between attempts changes the image, prompt, and render preview together so the row does not imply false combinations.

### Right Drawer

The drawer contains:

- time range edit controls
- audio preview and repeated playback for the shot range
- full lyrics text
- full shot note editor
- selected image controls
- prompt KO full text
- prompt EN full text
- attempt list and comparison
- rendered video player
- workflow template selector
- execution mode selector
- basic render parameters
- render queue action
- status actions
- review note

Prompt text can be edited in the drawer. Full prompts are not expanded directly in the table.

### Modal Usage

Modals are not the main workspace. They are used only for large video preview or focused comparison.

### Asset Picker

MVP asset picker is intentionally simple:

- show thumbnails from the project asset folder
- support browser upload
- select an image for the current shot
- create a new attempt draft when image selection changes

MVP excludes asset tags, favorites, rejected-asset state, and usage counts.

## Execution Modules

### Audio Align

The app runs alignment by default from the uploaded audio and lyrics. Alignment results create draft shots.

Users can edit the generated rows and time ranges. MVP row editing includes adding rows, deleting rows, and directly editing time ranges. A full timeline editor is out of scope.

### Prompt Generation

The default provider is Codex CLI.

The app calls Codex with:

- selected image as an image input
- visual bible snapshot
- lyrics
- speaker
- shot note
- time range and duration
- prior attempt context, when relevant
- LTX prompt rules

The expected structured output includes:

- image observations
- motion/camera plan
- prompt KO
- prompt EN
- negative rules when needed
- short rationale

The user reviews and edits generated prompts before rendering.

OpenAI API is excluded from MVP. Ollama running on the ComfyUI server can remain an optional fallback/helper, but it is not the default prompt writer.

### Video Render

The render module calls ComfyUI API.

Queue behavior:

- users can queue multiple jobs
- MVP worker executes one job at a time
- browser can close while jobs continue
- failed jobs are recorded and the queue continues
- retry creates a new job and preserves prior evidence
- cleanup runs between jobs where supported

MVP uses ComfyUI `/view` for previewing output files stored on the render server. A separate read-only media server can be added later if `/view` becomes limiting.

### Export

MVP export gathers selected clips into an export folder and writes metadata.

Export includes:

- selected video clips
- shot list CSV or JSON
- prompt, seed, workflow, and attempt snapshot JSON

Google Drive upload is out of MVP scope.

## Workflow and ComfyUI Model

The app separates workflow files from execution behavior.

### WorkflowTemplate

A `WorkflowTemplate` is a ComfyUI workflow JSON file, such as `LTX 2.3 All-In-One`.

Stored fields:

- name
- JSON path
- hash or version
- compatibility notes

### ExecutionMode

An `ExecutionMode` describes how to run a mode inside a workflow template.

Example modes:

- `lipsync_i2v`
- `plain_i2v`
- `start_end`
- `input_video`

Each mode defines:

- required inputs
- optional inputs
- node bindings for patching
- validation rules
- exposed basic parameters

### MVP Parameters

MVP exposes only basic render parameters:

- seed
- fps
- duration or frame count
- width
- height
- cfg
- steps
- filename prefix, if needed

Mode-specific advanced controls and arbitrary node patch editing are out of scope for MVP, but the data model stores parameter overrides in a way that can expand later.

### Render Snapshot

Before submission, the app patches the workflow template using the selected execution mode, inputs, prompts, and basic params.

The final patched workflow JSON is stored on the attempt before or during submission. This is required for reproducibility.

## Storage and Deployment

### Machine Roles

Small server:

- FastAPI backend
- React frontend static hosting
- SQLite DB
- job queue
- Codex CLI execution
- project metadata
- input files
- thumbnails or proxies
- selected outputs when needed

Large server:

- ComfyUI
- optional Ollama
- heavy render outputs
- ComfyUI temp/output storage

Client machines:

- MacBook, Mac mini, or other browsers on the internal network

### Storage Policy

The small server has limited disk space and should not store every full-resolution render candidate long term.

Recommended MVP policy:

- metadata, DB, inputs, thumbnails, and selected copies live on the small server
- heavy render candidates live on the ComfyUI server
- output access uses ComfyUI output metadata and `/view`
- selected clips can be copied into export storage
- Google Drive is reserved for manual/future archive workflows

Storage records should avoid hard-coding brittle absolute paths where possible. Prefer storage backend identifiers plus relative paths, with resolved local paths treated as environment-specific.

## Technical Stack

MVP stack:

- Backend: Python FastAPI
- Frontend: React
- Database: SQLite
- Queue: DB-backed single worker
- Alignment: backend execution module
- Prompt generation: Codex CLI provider
- Rendering: ComfyUI API

The app should target a one-command local start flow such as:

```bash
eumpa_studio start
```

Configuration should include:

- data root
- ComfyUI URL
- Codex CLI path
- alignment settings
- output/cache paths

## MVP Acceptance Criteria

MVP is acceptable when a user can:

1. Create a project from audio, lyrics, visual bible, and image assets.
2. Run alignment and get draft shot rows.
3. Edit shot time ranges and notes.
4. Pick an image for a shot through the asset picker.
5. Generate KO/EN LTX prompts with Codex CLI using the selected image.
6. Choose a workflow template and execution mode.
7. Queue multiple render jobs while the worker runs them sequentially.
8. Preview candidate videos through ComfyUI output access.
9. Mark attempts as selected, redo, rejected, or failed.
10. Export selected clips and metadata to a project export folder.

## Deferred Features

- Google Drive upload/archive automation
- team login and permissions
- external review links
- asset tagging and favorites
- AI quality review
- review/contact sheet generation
- workflow graph editor
- arbitrary JSON patch editor
- mode-specific advanced parameter panels
- multiple render workers
- Postgres deployment
- separate media server on the ComfyUI machine
