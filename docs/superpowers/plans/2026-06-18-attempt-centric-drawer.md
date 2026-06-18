# Attempt-Centric Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move reference image, prompt, workflow, render, and review controls inside expandable attempt cards so each attempt owns the inputs that produced it.

**Architecture:** Add shot-scoped attempt create/duplicate APIs and make the existing attempt PATCH route update image fields while protecting rendered attempts from input mutation. Refactor `ShotDrawer.tsx` so the drawer keeps shot-level context globally, while attempt-specific controls live in an expanded attempt card.

**Tech Stack:** FastAPI, SQLAlchemy, React, Vitest, Testing Library, CSS.

---

### Task 1: Backend Attempt Lifecycle

**Files:**
- Modify: `src/eumpa_studio/server/routes/shots.py`
- Test: `tests/backend/test_shots.py`

- [x] **Step 1: Write failing backend tests**

Add tests proving:

```python
def test_create_attempt_makes_it_active(...):
    response = api_client.post(f"/api/shots/{shot.id}/attempts", json={})
    assert response.status_code == 201
    assert db_session.get(Shot, shot.id).active_attempt_id == response.json()["id"]
```

```python
def test_duplicate_attempt_copies_inputs_and_clears_outputs(...):
    response = api_client.post(f"/api/shots/{shot.id}/attempts/{attempt.id}/duplicate")
    body = response.json()
    assert body["image_relative_path"] == attempt.image_relative_path
    assert body["prompt_en"] == attempt.prompt_en
    assert body["output_metadata"] is None
```

```python
def test_rendered_attempt_rejects_input_mutation(...):
    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={"prompt_en": "changed"},
    )
    assert response.status_code == 422
```

- [x] **Step 2: Verify RED**

Run:

```bash
uv run pytest tests/backend/test_shots.py -q
```

Expected: new tests fail because create/duplicate routes and rendered-attempt guard do not exist.

- [x] **Step 3: Implement backend**

Add:

- `AttemptCreate` body with optional image/prompt/workflow fields.
- `POST /shots/{shot_id}/attempts`.
- `POST /shots/{shot_id}/attempts/{attempt_id}/duplicate`.
- image fields in `AttemptUpdate`.
- `_reject_rendered_input_mutation()` for input-defining fields.

- [x] **Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/backend/test_shots.py -q
```

Expected: pass.

### Task 2: Frontend API And Tests

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Modify: `apps/web/src/components/ShotDrawer.test.tsx`

- [x] **Step 1: Write failing frontend tests**

Add tests proving:

- `New attempt` creates and expands an empty active attempt.
- Expanded attempt card contains image picker, prompt fields, workflow selectors, render button, and review controls.
- Selecting an asset updates the current attempt via PATCH and does not call the old `use-for-shot` route.
- Rendered attempt input fields are read-only and duplicate creates a new editable attempt.

- [x] **Step 2: Verify RED**

Run:

```bash
pnpm test -- src/components/ShotDrawer.test.tsx
```

Expected: new tests fail because controls are still global.

- [x] **Step 3: Add client helpers**

Add:

- `createAttempt(shotId, body)`.
- `duplicateAttempt(shotId, attemptId)`.
- extend `savePrompt()` body support for image fields.

### Task 3: Attempt-Centric Drawer UI

**Files:**
- Modify: `apps/web/src/components/ShotDrawer.tsx`
- Modify: `apps/web/src/components/AssetPicker.tsx`
- Modify: `apps/web/src/styles/app.css`

- [x] **Step 1: Refactor card state**

Track expanded attempt ID. New attempts and duplicates become active and expanded.

- [x] **Step 2: Move controls inside the card**

Expanded `AttemptCard` owns:

- reference image picker,
- prompt editors,
- workflow/mode selectors,
- queue render button,
- review controls.

- [x] **Step 3: Remove global attempt-input sections**

Remove global Prompt and Render settings sections. Keep Shot context and Attempts.

- [x] **Step 4: Read-only rendered attempts**

Disable input editors and workflow selectors when `attempt.output_metadata` exists. Show `Duplicate to new attempt`.

- [x] **Step 5: Styling**

Keep the operational dark UI, but make attempt cards denser and easier to scan. Use the image thumbnail as the visual anchor, and keep destructive actions low emphasis.

### Task 4: Verification And Delivery

**Files:**
- All modified files.

- [x] Run:

```bash
uv run pytest tests/backend -q
pnpm test
pnpm build
git diff --check
```

- [x] Restart local backend and verify in the in-app browser at `http://localhost:5173/`.
- [x] Confirm asset thumbnail click inside a card updates that attempt and does not create another attempt.
- [x] Confirm rendered attempt duplication creates a new editable attempt.
- [ ] Commit, push, create PR, and merge if checks pass.
