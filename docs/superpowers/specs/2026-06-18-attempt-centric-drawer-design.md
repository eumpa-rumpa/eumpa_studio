# Attempt-Centric Shot Drawer Design

## Goal

Make each attempt read as a self-contained production version. A user should be able to open one attempt and immediately see which reference image, prompt, workflow, render output, and review state produced it.

## Problem

The current drawer still separates attempt cards from the inputs that define an attempt:

- Attempt cards show status and a prompt preview.
- Reference image selection lives below the attempt list.
- Prompt editing lives in a global Prompt section.
- Workflow and mode selection live in a global Render settings section.

This makes it hard to answer: "Which image and prompt did this attempt use?"

## Product Direction

Use an attempt-centric layout:

1. The drawer header and Shot context stay shot-level.
2. The Attempts section becomes the main working area.
3. Each attempt is an expandable card.
4. Inputs that affect an attempt move inside that attempt card.
5. Creating a different image/prompt/workflow combination creates a new attempt instead of silently overwriting history.

## Attempt Card States

Collapsed card:

- Status pill.
- Active marker.
- Reference image thumbnail or "No image".
- Prompt preview.
- Workflow/mode readiness.
- Output/review marker.
- Actions: Expand, Use, Duplicate, Delete.

Expanded card:

- Reference image picker scoped to this attempt.
- Korean and English prompt editors scoped to this attempt.
- Workflow template and execution mode selectors scoped to this attempt.
- Queue Render action for this attempt.
- Video/review controls scoped to this attempt.

## Editing Rules

Attempts are editable only while they have not produced output.

- If `output_metadata` is null, the card can directly edit image, prompt, workflow, and mode.
- If `output_metadata` exists, input fields are read-only and the card exposes `Duplicate to new attempt`.
- Duplicating copies image, prompts, workflow, mode, and shot note snapshot into a new editable attempt, then makes that new attempt active.

This preserves render history and prevents accidental mutation of an already-rendered attempt.

## Creating Attempts

The drawer should have a primary `New attempt` action near the Attempts heading.

New attempt flow:

1. User clicks `New attempt`.
2. Backend creates an empty attempt for the shot.
3. UI expands the new card and makes it active.
4. User selects reference image, edits prompt, selects workflow/mode, and queues render from that card.

Existing project assets remain available in a compact asset picker inside the expanded card. Clicking an asset thumbnail only selects it for the currently expanded editable attempt; it must not create another attempt by itself.

## Render UX

Queue Render belongs inside the expanded attempt card. The sticky drawer summary can still show active attempt readiness, but the actionable render button should be visually tied to the attempt whose inputs will be used.

Disabled reasons are attempt-specific:

- Add or select a reference image when the chosen execution mode requires image input.
- Add a prompt when the mode requires prompt input.
- Choose workflow and mode.
- Selected workflow file is missing.
- Rendered attempts must be duplicated before changing inputs.

## Backend Needs

Reuse the existing `PATCH /api/shots/{shot_id}/attempts/{attempt_id}` route for prompt/workflow updates.

Add these attempt APIs:

- `POST /api/shots/{shot_id}/attempts` creates an empty attempt.
- `POST /api/shots/{shot_id}/attempts/{attempt_id}/duplicate` creates an editable copy.
- `PATCH /api/shots/{shot_id}/attempts/{attempt_id}` can update image fields as well as prompt/workflow fields.

Creating or duplicating an attempt makes the new attempt active by default. The backend rejects direct mutation of rendered attempts for fields that define render input.

## Frontend Structure

`ShotDrawer.tsx` can stay as the drawer container, but attempt-specific editing should move into local helper components or a new focused component:

- `AttemptCard`: collapsed/expanded shell and summary.
- `AttemptEditor`: image, prompt, workflow, render, and review controls for one attempt.
- `AttemptReadiness`: pure helper for disabled reason and readiness label.

The global Prompt and Render settings sections should be removed after their controls move into `AttemptEditor`.

## Testing

Backend:

- Creating an empty attempt makes it active.
- Duplicating a rendered attempt copies defining inputs but clears output/review/runtime fields.
- Mutating render-defining fields on a rendered attempt returns an error.
- Updating image/prompt/workflow on an editable attempt still works.

Frontend:

- Attempt card shows image thumbnail, prompt preview, workflow readiness, and active marker.
- Expanding an attempt reveals image, prompt, workflow, render, and review controls in the same card.
- Clicking an asset thumbnail inside an expanded card updates that attempt and does not create another attempt.
- Render button disabled reasons are scoped to the expanded attempt.
- Rendered attempt inputs are read-only and Duplicate creates a new editable attempt.

## Out Of Scope

- Deleting physical asset or output files.
- Multi-select bulk attempt operations.
- Full visual diffing between attempts.
- Changing the shot table layout.
