# Shot Drawer Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the shot drawer into a clearer production workflow with collapsible sections, primary render CTA, explicit attempt cards, and attempt deletion.

**Architecture:** Keep `ShotDrawer.tsx` as the container but add small local helper components for collapsible sections, active summary, status pills, and attempt cards. Add one backend attempt delete route and one frontend API helper.

**Tech Stack:** FastAPI, SQLAlchemy, React, Vitest, Testing Library, CSS.

---

### Task 1: Backend Attempt Delete

**Files:**
- Modify: `src/eumpa_studio/server/routes/shots.py`
- Test: `tests/backend/test_shots.py`

- [ ] Write backend tests for deleting inactive, active, and wrong-shot attempts.
- [ ] Run `uv run pytest tests/backend/test_shots.py -q` and confirm the new tests fail with 405 or missing route.
- [ ] Add `DELETE /api/shots/{shot_id}/attempts/{attempt_id}`.
- [ ] Run `uv run pytest tests/backend/test_shots.py -q` and confirm pass.

### Task 2: Frontend Drawer Workflow Tests

**Files:**
- Modify: `apps/web/src/components/ShotDrawer.test.tsx`

- [ ] Add tests for collapsible sections, sticky/summary render CTA, disabled reason, attempt card actions, and delete action.
- [ ] Run `pnpm test -- src/components/ShotDrawer.test.tsx` and confirm failures are from missing UI/API behavior.

### Task 3: Frontend API And Drawer Behavior

**Files:**
- Modify: `apps/web/src/api/client.ts`
- Modify: `apps/web/src/components/ShotDrawer.tsx`
- Modify: `apps/web/src/styles/app.css`

- [ ] Add `deleteAttempt(shotId, attemptId)`.
- [ ] Add collapsible `DrawerSection`.
- [ ] Add `ActiveAttemptSummary`.
- [ ] Add explicit `AttemptCard` actions.
- [ ] Move Queue Render to active summary and sticky footer.
- [ ] Keep render settings folded but editable.
- [ ] Add disabled render reason copy.
- [ ] Add deletion handler that refreshes attempt and shot state conservatively.

### Task 4: Verification And Delivery

**Files:**
- All modified files.

- [ ] Run `uv run pytest tests/backend -q`.
- [ ] Run `pnpm test`, `pnpm typecheck`, `pnpm build`.
- [ ] Run `git diff --check`.
- [ ] Restart local backend if needed.
- [ ] Verify directly in browser at `http://localhost:5173/`.
- [ ] Update Linear tickets with evidence.
- [ ] Commit, push, open PR, and merge if checks pass.
