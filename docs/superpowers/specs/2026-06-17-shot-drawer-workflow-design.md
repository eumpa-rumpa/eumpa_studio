# Shot Drawer Workflow Design

## Goal

Make the shot drawer read like a production workflow instead of a long list of controls. The user should always know which attempt is active, why render can or cannot be queued, and where to manage attempts.

## Scope

This pass covers Linear EPR-33, EPR-34, EPR-35, and EPR-36.

## Layout

The drawer keeps the current right-side panel but changes its hierarchy:

1. Header: shot number, time range, close button.
2. Active attempt summary: status, prompt/render readiness, selected reference state, primary Queue Render action, and the current disabled reason when render cannot run.
3. Collapsible sections:
   - Shot context: time range, audio preview, lyrics, shot note.
   - Attempts: attempt cards and reference image picker.
   - Prompt: generate, edit, save.
   - Render settings: workflow template and execution mode.
   - Review: play video, selected/redo/rejected, review note.

Default open sections: Shot context, Attempts, Prompt, Render settings. Review starts closed unless the active attempt has video output or review notes.

## Attempt UX

Attempts are cards, not whole-row selection buttons. Each card shows:

- Status pill with mapped color.
- Active marker when it is the current attempt.
- Prompt preview.
- Created timestamp.
- Render readiness text.
- Actions: Use, Selected, Redo, Reject, Delete.

Clicking random card space does not mutate state. State-changing actions are explicit.

## Render UX

Queue Render is a primary action in the active attempt summary and sticky footer. Render settings remain inside their folded section. When Queue Render is disabled, the UI shows one reason:

- Select or create an attempt.
- Choose a workflow and mode.
- Selected workflow file is missing.

## Backend Behavior

Add a scoped delete endpoint:

`DELETE /api/shots/{shot_id}/attempts/{attempt_id}`

Rules:

- Return 204 when an attempt for the shot is deleted.
- Return 404 when the attempt does not belong to the shot.
- If deleting the active attempt, clear `shot.active_attempt_id` and set the shot status to `Needs Input`.
- Do not delete related files in this pass. This avoids accidental asset loss because attempts can point at shared project assets.

## Testing

Backend:

- Deleting inactive attempt removes it and leaves active attempt unchanged.
- Deleting active attempt clears active attempt and updates shot status.
- Deleting an attempt from another shot returns 404.

Frontend:

- Collapsible sections can close while Queue Render remains reachable.
- Disabled render reason is visible.
- Attempt cards show active marker and explicit Use/Delete actions.
- Delete removes the attempt from the visible list.

## Notes For User Review

The only product decision made without further interruption: attempt deletion removes the DB attempt only, not referenced assets or generated output files. That is safer for this pass because attempts may share reference assets.
