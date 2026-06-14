import { useEffect, useMemo, useState } from "react";
import {
  fetchShotAttempts,
  updateAttemptReviewNote,
  updateShot,
} from "../api/client";
import type { Attempt, Shot } from "../api/types";

interface ShotDrawerProps {
  shot: Shot | null;
  projectId: string;
  onClose: () => void;
  onShotUpdated: () => void;
}

const STATUS_ACTIONS = [
  { label: "Mark Ready", value: "Ready" },
  { label: "Mark Redo", value: "Redo" },
  { label: "Mark Rejected", value: "Rejected" },
] as const;

function formatSeconds(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function previewText(value: string | null, maxLength: number): string {
  if (!value) return "No prompt";
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

export function ShotDrawer({ shot, projectId, onClose, onShotUpdated }: ShotDrawerProps) {
  const [currentShot, setCurrentShot] = useState<Shot | null>(shot);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [shotNote, setShotNote] = useState("");
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [reviewNote, setReviewNote] = useState("");
  const [loadingAttempts, setLoadingAttempts] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const activeAttempt = useMemo(() => {
    if (!currentShot?.active_attempt_id) return null;
    return attempts.find((attempt) => attempt.id === currentShot.active_attempt_id) ?? null;
  }, [attempts, currentShot?.active_attempt_id]);

  useEffect(() => {
    setCurrentShot(shot);
    setStartTime(shot ? String(shot.start_time) : "");
    setEndTime(shot ? String(shot.end_time) : "");
    setShotNote(shot?.shot_note ?? "");
    setError(null);
  }, [shot]);

  useEffect(() => {
    if (!shot) {
      setAttempts([]);
      return;
    }

    let cancelled = false;
    setLoadingAttempts(true);
    setError(null);

    fetchShotAttempts(shot.id)
      .then((data) => {
        if (!cancelled) {
          setAttempts(data);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load attempts");
          setAttempts([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingAttempts(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [shot]);

  useEffect(() => {
    setReviewNote(activeAttempt?.review_note ?? "");
  }, [activeAttempt]);

  if (!currentShot) {
    return null;
  }

  async function saveShotFields(body: Parameters<typeof updateShot>[1], label: string) {
    if (!currentShot) return;

    try {
      setSaving(label);
      setError(null);
      const updatedShot = await updateShot(currentShot.id, body);
      setCurrentShot(updatedShot);
      setStartTime(String(updatedShot.start_time));
      setEndTime(String(updatedShot.end_time));
      setShotNote(updatedShot.shot_note ?? "");
      onShotUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save shot");
    } finally {
      setSaving(null);
    }
  }

  function saveTimeRange() {
    void saveShotFields(
      {
        start_time: Number(startTime),
        end_time: Number(endTime),
      },
      "time",
    );
  }

  function saveShotNote() {
    if (!currentShot) return;
    if (shotNote === (currentShot.shot_note ?? "")) return;
    void saveShotFields({ shot_note: shotNote }, "shot-note");
  }

  function markStatus(status: string) {
    void saveShotFields({ status }, `status-${status}`);
  }

  function selectAttempt(attemptId: string) {
    if (!currentShot) return;
    if (attemptId === currentShot.active_attempt_id) return;
    void saveShotFields({ active_attempt_id: attemptId }, `attempt-${attemptId}`);
  }

  async function saveReviewNote() {
    if (!currentShot || !activeAttempt) return;

    try {
      setSaving("review-note");
      setError(null);
      const updatedAttempt = await updateAttemptReviewNote(
        currentShot.id,
        activeAttempt.id,
        reviewNote,
      );
      setAttempts((items) =>
        items.map((item) => (item.id === updatedAttempt.id ? updatedAttempt : item)),
      );
      onShotUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save review note");
    } finally {
      setSaving(null);
    }
  }

  return (
    <aside
      className="shot-drawer"
      aria-label="Shot editor"
      data-project-id={projectId}
    >
      <div className="shot-drawer__header">
        <div>
          <p className="shot-drawer__eyebrow">Shot #{currentShot.order + 1}</p>
          <h2 className="shot-drawer__title">
            {formatSeconds(currentShot.start_time)}-{formatSeconds(currentShot.end_time)}s
          </h2>
        </div>
        <button type="button" className="shot-drawer__close" onClick={onClose} aria-label="Close drawer">
          x
        </button>
      </div>

      {error ? <p className="shot-drawer__error">{error}</p> : null}

      <section className="shot-drawer__section" aria-labelledby="time-range-heading">
        <h3 id="time-range-heading" className="shot-drawer__section-title">
          Time Range
        </h3>
        <div className="shot-drawer__field-row">
          <label className="shot-drawer__field">
            <span>Start</span>
            <input
              type="number"
              step="0.1"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
            />
          </label>
          <label className="shot-drawer__field">
            <span>End</span>
            <input
              type="number"
              step="0.1"
              value={endTime}
              onChange={(event) => setEndTime(event.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="shot-drawer__button"
          onClick={saveTimeRange}
          disabled={saving === "time"}
        >
          Save
        </button>
      </section>

      <section className="shot-drawer__section" aria-labelledby="lyrics-heading">
        <h3 id="lyrics-heading" className="shot-drawer__section-title">
          Full Lyrics
        </h3>
        <div className="shot-drawer__readonly">{currentShot.lyrics_text || "—"}</div>
      </section>

      <section className="shot-drawer__section" aria-labelledby="shot-note-heading">
        <h3 id="shot-note-heading" className="shot-drawer__section-title">
          Shot Note
        </h3>
        <textarea
          className="shot-drawer__textarea"
          value={shotNote}
          onChange={(event) => setShotNote(event.target.value)}
          onBlur={saveShotNote}
          rows={5}
        />
      </section>

      <section className="shot-drawer__section" aria-labelledby="attempts-heading">
        <h3 id="attempts-heading" className="shot-drawer__section-title">
          Attempts
        </h3>
        {loadingAttempts ? <p className="shot-drawer__muted">Loading attempts...</p> : null}
        {!loadingAttempts && attempts.length === 0 ? (
          <p className="shot-drawer__muted">No attempts yet.</p>
        ) : null}
        <div className="shot-drawer__attempts">
          {attempts.map((attempt) => (
            <button
              key={attempt.id}
              type="button"
              className={
                attempt.id === currentShot.active_attempt_id
                  ? "shot-drawer__attempt shot-drawer__attempt--active"
                  : "shot-drawer__attempt"
              }
              onClick={() => selectAttempt(attempt.id)}
            >
              <span className="shot-drawer__status">{attempt.status}</span>
              <span className="shot-drawer__attempt-preview">
                {previewText(attempt.prompt_ko, 80)}
              </span>
              <time className="shot-drawer__attempt-date" dateTime={attempt.created_at}>
                {formatDate(attempt.created_at)}
              </time>
            </button>
          ))}
        </div>
      </section>

      <section className="shot-drawer__section" aria-labelledby="active-attempt-heading">
        <h3 id="active-attempt-heading" className="shot-drawer__section-title">
          Active Attempt
        </h3>
        {activeAttempt ? (
          <div className="shot-drawer__prompt-grid">
            <label className="shot-drawer__field">
              <span>Prompt KO</span>
              <textarea
                className="shot-drawer__textarea"
                value={activeAttempt.prompt_ko ?? ""}
                readOnly
                rows={6}
              />
            </label>
            <label className="shot-drawer__field">
              <span>Prompt EN</span>
              <textarea
                className="shot-drawer__textarea"
                value={activeAttempt.prompt_en ?? ""}
                readOnly
                rows={6}
              />
            </label>
          </div>
        ) : (
          <p className="shot-drawer__muted">No active attempt selected.</p>
        )}
      </section>

      <section className="shot-drawer__section" aria-labelledby="status-actions-heading">
        <h3 id="status-actions-heading" className="shot-drawer__section-title">
          Status Actions
        </h3>
        <div className="shot-drawer__actions">
          {STATUS_ACTIONS.map((action) => (
            <button
              key={action.value}
              type="button"
              className="shot-drawer__button"
              onClick={() => markStatus(action.value)}
              disabled={saving === `status-${action.value}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </section>

      <section className="shot-drawer__section" aria-labelledby="review-note-heading">
        <h3 id="review-note-heading" className="shot-drawer__section-title">
          Review Note
        </h3>
        <textarea
          className="shot-drawer__textarea"
          value={reviewNote}
          onChange={(event) => setReviewNote(event.target.value)}
          rows={5}
          disabled={!activeAttempt}
        />
        <button
          type="button"
          className="shot-drawer__button"
          onClick={saveReviewNote}
          disabled={!activeAttempt || saving === "review-note"}
        >
          Save
        </button>
      </section>
    </aside>
  );
}
