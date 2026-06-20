import type { Shot } from "../api/types";
import { createShot, enqueueAlignment } from "../api/client";
import { useShots } from "../hooks/useShots";
import { useState } from "react";

interface ShotTableProps {
  projectId: string;
  onShotSelect?: (shot: Shot) => void;
  onJobsUpdated?: () => void;
}

function previewText(value: string | null, maxLength: number): string {
  if (!value) return "—";
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

function filenameFromPath(value: string | null): string | null {
  if (!value) return null;
  const parts = value.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? value;
}

function formatSeconds(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

function getAttemptLabel(shot: Shot): string {
  if (shot.active_attempt) {
    return `Active / ${Math.max(shot.attempt_count, 1)}`;
  }

  if (shot.attempt_count === 1) return "1 attempt";
  return `${shot.attempt_count} attempts`;
}

function getPromptPreview(shot: Shot): string {
  return previewText(shot.active_attempt?.prompt_ko ?? shot.active_attempt?.prompt_en ?? "No prompt", 84);
}

function ShotReferenceImageState({ shot }: { shot: Shot }) {
  const imageLabel = filenameFromPath(shot.active_attempt?.image_relative_path ?? null);

  return (
    <span
      className={imageLabel ? "shot-table__image-chip" : "shot-table__image-chip shot-table__image-chip--empty"}
      title={imageLabel ?? "No image"}
    >
      <span className="shot-table__image-thumb" aria-hidden="true" />
      <span className="shot-table__image-label">{imageLabel ?? "No image"}</span>
    </span>
  );
}

function ShotAttemptOverview({ shot }: { shot: Shot }) {
  return (
    <span className="shot-table__attempt-overview">
      <span className="shot-table__attempt-row">
        <span className="shot-table__badge">{getAttemptLabel(shot)}</span>
        {shot.active_attempt ? (
          <span className="shot-table__attempt-status">{shot.active_attempt.status}</span>
        ) : null}
      </span>
      <span className="shot-table__attempt-assets">
        <ShotReferenceImageState shot={shot} />
        <span className="shot-table__prompt-chip" title={getPromptPreview(shot)}>
          {getPromptPreview(shot)}
        </span>
        <ShotVideoPreview shot={shot} />
      </span>
    </span>
  );
}

function ShotVideoPreview({ shot }: { shot: Shot }) {
  const videoUrl = shot.active_attempt?.video_url;
  if (!videoUrl) {
    return (
      <span className="shot-table__preview-empty">
        {shot.active_attempt ? "Needs render" : "No render"}
      </span>
    );
  }

  return (
    <video
      className="shot-table__video"
      aria-label={`Video preview for shot ${shot.order + 1}`}
      src={videoUrl}
      controls
      muted
      preload="metadata"
      onClick={(event) => event.stopPropagation()}
    />
  );
}

export function ShotTable({ projectId, onShotSelect, onJobsUpdated }: ShotTableProps) {
  const { shots, loading, error, refetch } = useShots(projectId);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] = useState<string | null>(null);

  function selectShot(shot: Shot) {
    onShotSelect?.(shot);
  }

  async function runAlignment() {
    setSubmittingAction("alignment");
    setActionError(null);
    setActionMessage(null);
    try {
      await enqueueAlignment(projectId);
      setActionMessage("Alignment job queued");
      onJobsUpdated?.();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to queue alignment");
    } finally {
      setSubmittingAction(null);
    }
  }

  async function addManualShot() {
    setSubmittingAction("manual-shot");
    setActionError(null);
    setActionMessage(null);
    try {
      const shot = await createShot(projectId, {
        order: shots.length,
        start_time: shots.length * 5,
        end_time: shots.length * 5 + 5,
        status: "Needs Input",
        lyrics_text: "",
        shot_note: "",
      });
      setActionMessage("Manual shot added");
      refetch();
      onShotSelect?.(shot);
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to add manual shot");
    } finally {
      setSubmittingAction(null);
    }
  }

  const productionActions = (
    <div className="shot-table__toolbar" aria-label="Shot setup actions">
      <p className="shot-table__hint">
        Use alignment for a lyric-based pass, or add a manual shot when you want to block scenes yourself.
      </p>
      <div className="shot-table__empty-actions">
        <button
          type="button"
          className="button button--primary"
          onClick={() => { void runAlignment(); }}
          disabled={submittingAction !== null}
        >
          {submittingAction === "alignment" ? "Queueing..." : "Run alignment"}
        </button>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => { void addManualShot(); }}
          disabled={submittingAction !== null}
        >
          {submittingAction === "manual-shot" ? "Adding..." : "Add manual shot"}
        </button>
      </div>
      {actionMessage ? <p className="shot-table__notice">{actionMessage}</p> : null}
      {actionError ? <p className="shot-table__state shot-table__state--error">{actionError}</p> : null}
    </div>
  );

  if (loading) {
    return <p className="shot-table__state">Loading shots...</p>;
  }

  if (error) {
    return <p className="shot-table__state shot-table__state--error">{error}</p>;
  }

  if (shots.length === 0) {
    return (
      <div className="shot-table__empty">
        <p className="shot-table__state">No shots yet. Run alignment to generate shots.</p>
        {productionActions}
      </div>
    );
  }

  return (
    <div className="shot-table__stack">
      {productionActions}
      <div className="shot-table" aria-label="Shot production table">
        <table className="shot-table__table">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Time</th>
              <th scope="col">Speaker</th>
              <th scope="col">Lyrics</th>
              <th scope="col">Note</th>
              <th scope="col">Attempt</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {shots.map((shot) => (
              <tr
                key={shot.id}
                className="shot-table__row"
                tabIndex={0}
                onClick={() => selectShot(shot)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    selectShot(shot);
                  }
                }}
              >
                <td className="shot-table__index" data-label="#">
                  {shot.order + 1}
                </td>
                <td className="shot-table__time" data-label="Time">
                  {formatSeconds(shot.start_time)}-{formatSeconds(shot.end_time)}s
                </td>
                <td data-label="Speaker">{shot.speaker ?? "—"}</td>
                <td className="shot-table__preview" data-label="Lyrics">
                  {previewText(shot.lyrics_text, 58)}
                </td>
                <td className="shot-table__note" data-label="Note">
                  {previewText(shot.shot_note, 54)}
                </td>
                <td className="shot-table__attempt-cell" data-label="Attempt">
                  <ShotAttemptOverview shot={shot} />
                </td>
                <td data-label="Status">
                  <span className="shot-table__status">{shot.status}</span>
                </td>
                <td className="shot-table__action-cell" data-label="Actions">
                  <button
                    type="button"
                    className="shot-table__open"
                    onClick={(event) => {
                      event.stopPropagation();
                      selectShot(shot);
                    }}
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
