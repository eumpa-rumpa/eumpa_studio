# Drawer Input Polish Tickets

Linear creation was attempted on 2026-06-18, but the connector returned
`Tool name linear.list_issues does not match resource uri .../list_issues`.
These ticket logs mirror the work implemented in this branch so they can be
copied into Linear when the connector is healthy.

## Ticket 1: Clarify skill workflow sync feedback

- Replace the ambiguous `Add skill LTX workflow` button with `Sync skill LTX workflow`.
- Show explicit success copy after syncing the bundled skill workflow into the project.
- Confirm the workflow path points at the project copy under `data/workflows/skill-defaults`.

## Ticket 2: Make attempt expansion user-controlled

- Default the latest or active attempt open when a drawer loads.
- Allow every attempt card to be collapsed, including the active/latest one.
- Keep attempt-owned controls hidden while the card is collapsed.

## Ticket 3: Split reference inputs into start and optional end images

- Replace the single reference-image picker with start and end image slots.
- Save start image to `image_*` fields and optional end image to `end_image_*` fields.
- Add a clear action for optional end images.

## Ticket 4: Generate prompts from attempt shot note and editable system prompt

- Add an attempt-owned shot note input inside the prompt section.
- Add a collapsible editable system prompt with a default LTX prompt-generation instruction.
- Save the attempt note before prompt generation and pass the edited system prompt to `/api/prompts/generate`.
- Pass start and optional end image paths into the Codex prompt context.
