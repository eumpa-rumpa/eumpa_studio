import { useState } from "react";
import { VideoPreviewModal } from "./VideoPreviewModal";

const BASE_URL = "/api";

interface ShotDrawerProps {
  shotId: string;
  attemptId: string;
  onClose: () => void;
}

type ReviewStatus = "Selected" | "Redo" | "Rejected";

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

export function ShotDrawer({ shotId, attemptId, onClose }: ShotDrawerProps) {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handlePlayVideo() {
    setVideoError(null);
    try {
      const url = await fetchVideoUrl(shotId, attemptId);
      setVideoUrl(url);
    } catch (err) {
      setVideoError(err instanceof Error ? err.message : "Failed to load video");
    }
  }

  async function handleReview(status: ReviewStatus) {
    setReviewError(null);
    setIsSaving(true);
    try {
      await postReview(shotId, attemptId, status);
      setReviewStatus(status);
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Failed to update review");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveNote() {
    setReviewError(null);
    setIsSaving(true);
    try {
      const status = reviewStatus ?? "Needs Review";
      await postReview(shotId, attemptId, status, reviewNote);
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <div className="shot-drawer" role="complementary" aria-label="Shot review panel">
        <div className="shot-drawer__header">
          <h2 className="shot-drawer__title">Review Attempt</h2>
          <button
            className="shot-drawer__close"
            aria-label="Close drawer"
            onClick={onClose}
            type="button"
          >
            ✕
          </button>
        </div>

        <section className="shot-drawer__review" aria-labelledby="review-section-title">
          <h3 id="review-section-title" className="shot-drawer__section-title">
            Review
          </h3>

          <div className="shot-drawer__video-row">
            <button
              className="shot-drawer__btn shot-drawer__btn--play"
              type="button"
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
                disabled={isSaving}
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
              onChange={(e) => setReviewNote(e.target.value)}
              rows={4}
              placeholder="Add a review note…"
            />
            <button
              className="shot-drawer__btn shot-drawer__btn--save"
              type="button"
              disabled={isSaving}
              onClick={() => void handleSaveNote()}
            >
              {isSaving ? "Saving…" : "Save Note"}
            </button>
          </div>

          {reviewError ? (
            <p className="shot-drawer__error" role="alert">
              {reviewError}
            </p>
          ) : null}
        </section>
      </div>

      <VideoPreviewModal
        videoUrl={videoUrl}
        onClose={() => setVideoUrl(null)}
      />
    </>
  );
}
