import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  fetchShotAttempts,
  generatePrompt as generatePromptRequest,
  savePrompt as savePromptRequest,
  updateShot,
} from "../api/client";
import type { Attempt, Shot } from "../api/types";
import { VideoPreviewModal } from "./VideoPreviewModal";

interface ShotDrawerProps {
  shot: Shot | null;
  projectId: string;
  onClose: () => void;
  onShotUpdated: () => void;
}

const BASE_URL = "/api";

type ReviewStatus = "Selected" | "Redo" | "Rejected";

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

async function fetchVideoUrl(shotId: string, attemptId: string): Promise<string> {
  const response = await fetch(
    `${BASE_URL}/shots/${shotId}/attempts/${attemptId}/video-url`
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  const data = (await response.json()) as { video_url: string };
  return data.video_url;
}

async function postReview(
  shotId: string,
  attemptId: string,
  status: string,
  reviewNote?: string
): Promise<void> {
  const body: { status: string; review_note?: string } = { status };
  if (reviewNote !== undefined) {
    body.review_note = reviewNote;
  }
  const response = await fetch(
    `${BASE_URL}/shots/${shotId}/attempts/${attemptId}/review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
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

  // Prompt generation state
  const [promptKo, setPromptKo] = useState("");
  const [promptEn, setPromptEn] = useState("");
  const [generating, setGenerating] = useState(false);
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  // Review/video state
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

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
    setPromptKo(activeAttempt?.prompt_ko ?? "");
    setPromptEn(activeAttempt?.prompt_en ?? "");
    setSavedMessage(null);
    setPromptError(null);
    setReviewStatus(null);
    setReviewError(null);
    setVideoUrl(null);
    setVideoError(null);
  }, [activeAttempt?.id, activeAttempt?.prompt_ko, activeAttempt?.prompt_en, activeAttempt?.review_note]);

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

  async function handleGenerate() {
    if (!activeAttempt) return;
    setPromptError(null);
    setSavedMessage(null);
    setGenerating(true);
    try {
      const updated = await generatePromptRequest(activeAttempt.id);
      setPromptKo(updated.prompt_ko ?? "");
      setPromptEn(updated.prompt_en ?? "");
      setAttempts((items) =>
        items.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)),
      );
    } catch (err: unknown) {
      setPromptError(err instanceof Error ? err.message : "Failed to generate prompt");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSavePrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentShot || !activeAttempt) return;
    setPromptError(null);
    setSavedMessage(null);
    setPromptSaving(true);
    try {
      const updated = await savePromptRequest(currentShot.id, activeAttempt.id, {
        prompt_ko: promptKo,
        prompt_en: promptEn,
      });
      setAttempts((items) =>
        items.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)),
      );
      setSavedMessage("Prompts saved");
    } catch (err: unknown) {
      setPromptError(err instanceof Error ? err.message : "Failed to save prompts");
    } finally {
      setPromptSaving(false);
    }
  }

  async function handlePlayVideo() {
    if (!currentShot || !activeAttempt) return;
    setVideoError(null);
    try {
      const url = await fetchVideoUrl(currentShot.id, activeAttempt.id);
      setVideoUrl(url);
    } catch (err: unknown) {
      setVideoError(err instanceof Error ? err.message : "Failed to load video");
    }
  }

  async function handleReview(status: ReviewStatus) {
    if (!currentShot || !activeAttempt) return;
    setReviewError(null);
    setReviewSaving(true);
    try {
      await postReview(currentShot.id, activeAttempt.id, status);
      setReviewStatus(status);
      onShotUpdated();
    } catch (err: unknown) {
      setReviewError(err instanceof Error ? err.message : "Failed to update review");
    } finally {
      setReviewSaving(false);
    }
  }

  async function handleSaveReviewWithNote() {
    if (!currentShot || !activeAttempt) return;
    setReviewError(null);
    setReviewSaving(true);
    try {
      const status = reviewStatus ?? "Needs Review";
      await postReview(currentShot.id, activeAttempt.id, status, reviewNote);
      onShotUpdated();
    } catch (err: unknown) {
      setReviewError(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setReviewSaving(false);
    }
  }

  return (
    <>
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

        {/* Prompt Generation Section (EPR-15) */}
        <section className="shot-drawer__section" aria-labelledby="prompt-gen-heading">
          <div className="shot-drawer__section-header">
            <h3 id="prompt-gen-heading" className="shot-drawer__section-title">
              Generate Prompt
            </h3>
            <button
              type="button"
              className="shot-drawer__action"
              disabled={activeAttempt === null || generating}
              onClick={() => { void handleGenerate(); }}
            >
              {generating ? (
                <>
                  <span className="shot-drawer__spinner" aria-hidden="true" />
                  Generating...
                </>
              ) : (
                "Generate Prompt"
              )}
            </button>
          </div>

          {promptError ? <p className="shot-drawer__error">{promptError}</p> : null}

          {activeAttempt === null ? (
            <p className="shot-drawer__empty">Select an attempt to generate prompts.</p>
          ) : (
            <form className="shot-drawer__prompt-form" onSubmit={(event) => { void handleSavePrompt(event); }}>
              <label className="shot-drawer__field" htmlFor="prompt-ko">
                <span>Korean prompt</span>
                <textarea
                  id="prompt-ko"
                  value={promptKo}
                  onChange={(event) => setPromptKo(event.target.value)}
                  rows={10}
                />
              </label>

              <label className="shot-drawer__field" htmlFor="prompt-en">
                <span>English prompt</span>
                <textarea
                  id="prompt-en"
                  value={promptEn}
                  onChange={(event) => setPromptEn(event.target.value)}
                  rows={10}
                />
              </label>

              <div className="shot-drawer__footer">
                {savedMessage ? <span className="shot-drawer__saved">{savedMessage}</span> : null}
                <button
                  type="submit"
                  className="shot-drawer__action shot-drawer__action--primary"
                  disabled={promptSaving}
                >
                  {promptSaving ? "Saving..." : "Save Prompts"}
                </button>
              </div>
            </form>
          )}
        </section>

        {/* Status Actions (existing) */}
        <section className="shot-drawer__section" aria-labelledby="status-actions-heading">
          <h3 id="status-actions-heading" className="shot-drawer__section-title">
            Status Actions
          </h3>
          <div className="shot-drawer__actions">
            {(["Mark Ready", "Mark Redo", "Mark Rejected"] as const).map((label) => {
              const value = label.replace("Mark ", "");
              return (
                <button
                  key={value}
                  type="button"
                  className="shot-drawer__button"
                  onClick={() => markStatus(value)}
                  disabled={saving === `status-${value}`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </section>

        {/* Review Section (EPR-18) */}
        <section className="shot-drawer__review" aria-labelledby="review-section-title">
          <h3 id="review-section-title" className="shot-drawer__section-title">
            Review
          </h3>

          <div className="shot-drawer__video-row">
            <button
              className="shot-drawer__btn shot-drawer__btn--play"
              type="button"
              disabled={!activeAttempt}
              onClick={() => void handlePlayVideo()}
            >
              Play Video
            </button>
            {videoError ? (
              <p className="shot-drawer__error" role="alert">
                {videoError}
              </p>
            ) : null}
          </div>

          <div className="shot-drawer__status-row" role="group" aria-label="Review status">
            {(["Selected", "Redo", "Rejected"] as ReviewStatus[]).map((status) => (
              <button
                key={status}
                className={`shot-drawer__btn shot-drawer__btn--status${
                  reviewStatus === status ? " shot-drawer__btn--active" : ""
                }`}
                type="button"
                disabled={reviewSaving || !activeAttempt}
                onClick={() => void handleReview(status)}
                aria-pressed={reviewStatus === status}
              >
                {status}
              </button>
            ))}
          </div>

          {reviewStatus ? (
            <p className="shot-drawer__status-label">
              Status set to: <strong>{reviewStatus}</strong>
            </p>
          ) : null}

          <div className="shot-drawer__note-row">
            <label htmlFor="review-note" className="shot-drawer__label">
              Review Note
            </label>
            <textarea
              id="review-note"
              className="shot-drawer__textarea"
              value={reviewNote}
              onChange={(event) => setReviewNote(event.target.value)}
              rows={4}
              placeholder="Add a review note…"
              disabled={!activeAttempt}
            />
            <button
              className="shot-drawer__btn shot-drawer__btn--save"
              type="button"
              disabled={reviewSaving || !activeAttempt}
              onClick={() => void handleSaveReviewWithNote()}
            >
              {reviewSaving ? "Saving…" : "Save Note"}
            </button>
          </div>

          {reviewError ? (
            <p className="shot-drawer__error" role="alert">
              {reviewError}
            </p>
          ) : null}
        </section>
      </aside>

      <VideoPreviewModal
        videoUrl={videoUrl}
        onClose={() => setVideoUrl(null)}
      />
    </>
  );
}
