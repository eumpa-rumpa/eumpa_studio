import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  createAttempt,
  deleteAttempt,
  duplicateAttempt,
  enqueueRender,
  fetchExecutionModes,
  fetchShotAttempts,
  fetchWorkflowTemplates,
  generatePrompt as generatePromptRequest,
  savePrompt as saveAttemptRequest,
  updateShot,
} from "../api/client";
import type { Asset, Attempt, ExecutionMode, Shot, WorkflowTemplate } from "../api/types";
import { AssetPicker } from "./AssetPicker";
import { VideoPreviewModal } from "./VideoPreviewModal";

interface ShotDrawerProps {
  shot: Shot | null;
  projectId: string;
  projectAudioAvailable?: boolean;
  onClose: () => void;
  onShotUpdated: () => void;
}

const BASE_URL = "/api";

type ReviewStatus = "Selected" | "Redo" | "Rejected";
type ImageRole = "start" | "end";

const DEFAULT_SYSTEM_PROMPT = [
  "Generate production-ready LTX image-to-video prompts for a music video shot.",
  "Use the shot note, lyrics, visual bible, and reference image roles.",
  "Preserve subject identity from the start image, use the optional end image as the target ending state, and describe motion, camera, staging, and lip-sync direction clearly.",
  "Return concise Korean and English prompts suitable for ComfyUI LTX rendering.",
].join(" ");

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

function filenameFromPath(value: string | null): string {
  if (!value) return "No reference image";
  const parts = value.split("/").filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : value;
}

function parseRequiredInputs(mode: ExecutionMode | null): string[] {
  if (!mode?.required_inputs) return [];
  try {
    const parsed = JSON.parse(mode.required_inputs) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}

async function fetchVideoUrl(shotId: string, attemptId: string): Promise<string> {
  const response = await fetch(
    `${BASE_URL}/shots/${shotId}/attempts/${attemptId}/video-url`,
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
  reviewNote?: string,
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
    },
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
}

interface ShotAudioPreviewProps {
  projectId: string;
  startTime: number;
  endTime: number;
  audioAvailable: boolean;
}

function ShotAudioPreview({
  projectId,
  startTime,
  endTime,
  audioAvailable,
}: ShotAudioPreviewProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const formattedRange = `${formatSeconds(startTime)}-${formatSeconds(endTime)}s`;
  const audioUrl = `/api/projects/${encodeURIComponent(projectId)}/audio#t=${formatSeconds(startTime)},${formatSeconds(endTime)}`;

  function seekToSegmentStart() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.currentTime < startTime || audio.currentTime >= endTime) {
      audio.currentTime = startTime;
    }
  }

  function stopAtSegmentEnd() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.currentTime >= endTime) {
      audio.pause();
      audio.currentTime = startTime;
    }
  }

  if (!audioAvailable) {
    return <p className="shot-drawer__muted">No project audio attached.</p>;
  }

  return (
    <audio
      ref={audioRef}
      className="shot-drawer__audio"
      aria-label={`Audio preview for ${formattedRange}`}
      controls
      preload="metadata"
      src={audioUrl}
      onLoadedMetadata={seekToSegmentStart}
      onPlay={seekToSegmentStart}
      onTimeUpdate={stopAtSegmentEnd}
    />
  );
}

type SectionKey = "context" | "attempts";

interface DrawerSectionProps {
  id: SectionKey;
  title: string;
  open: boolean;
  onToggle: (id: SectionKey) => void;
  children: ReactNode;
}

function DrawerSection({ id, title, open, onToggle, children }: DrawerSectionProps) {
  const label = `${open ? "Collapse" : "Expand"} ${title}`;
  return (
    <section className="shot-drawer__section" aria-labelledby={`${id}-section-heading`}>
      <button
        type="button"
        className="shot-drawer__section-toggle"
        aria-expanded={open}
        aria-label={label}
        onClick={() => onToggle(id)}
      >
        <span id={`${id}-section-heading`} className="shot-drawer__section-title">
          {title}
        </span>
        <span aria-hidden="true">{open ? "-" : "+"}</span>
      </button>
      {open ? <div className="shot-drawer__section-body">{children}</div> : null}
    </section>
  );
}

function attemptStatusTone(status: string): string {
  return status.toLowerCase().replace(/\s+/g, "-");
}

function attemptReadiness(attempt: Attempt): string {
  if (!attempt.workflow_template_id || !attempt.execution_mode_id) {
    return "Needs render setup";
  }
  if (!attempt.prompt_ko && !attempt.prompt_en) {
    return "Needs prompt";
  }
  if (attempt.output_metadata) {
    return "Rendered output";
  }
  return "Ready to render";
}

interface AttemptCardProps {
  attempt: Attempt;
  active: boolean;
  expanded: boolean;
  saving: boolean;
  deleting: boolean;
  onToggle: (attemptId: string) => void;
  onUse: (attemptId: string) => void;
  onDuplicate: (attemptId: string) => void;
  onDelete: (attemptId: string) => void;
  children: ReactNode;
}

function AttemptCard({
  attempt,
  active,
  expanded,
  saving,
  deleting,
  onToggle,
  onUse,
  onDuplicate,
  onDelete,
  children,
}: AttemptCardProps) {
  const rendered = Boolean(attempt.output_metadata);
  const preview = previewText(attempt.prompt_ko || attempt.prompt_en, 80);
  return (
    <article
      className={
        active
          ? "shot-drawer__attempt-card shot-drawer__attempt-card--active"
          : "shot-drawer__attempt-card"
      }
      aria-label={`Attempt ${attempt.id}`}
    >
      <button
        type="button"
        className="shot-drawer__attempt-toggle"
        aria-expanded={expanded}
        aria-label={`${expanded ? "Collapse" : "Expand"} attempt ${attempt.id}`}
        onClick={() => onToggle(attempt.id)}
      >
        <span className="shot-drawer__attempt-main">
          <span
            className={`shot-drawer__status shot-drawer__status--${attemptStatusTone(attempt.status)}`}
          >
            {attempt.status}
          </span>
          <span className="shot-drawer__attempt-preview">{preview}</span>
        </span>
        <span className="shot-drawer__attempt-side">
          {active ? <span className="shot-drawer__active-marker">Active</span> : null}
          <span className="shot-drawer__attempt-caret">{expanded ? "-" : "+"}</span>
        </span>
      </button>

      <div className="shot-drawer__attempt-meta">
        <span>{filenameFromPath(attempt.image_relative_path)}</span>
        <span>{attemptReadiness(attempt)}</span>
        <time dateTime={attempt.created_at}>{formatDate(attempt.created_at)}</time>
      </div>

      <div className="shot-drawer__attempt-actions">
        <button
          type="button"
          className="shot-drawer__btn"
          disabled={active || saving || deleting}
          aria-label={`Use attempt ${attempt.id}`}
          onClick={() => onUse(attempt.id)}
        >
          Use
        </button>
        {rendered ? (
          <button
            type="button"
            className="shot-drawer__btn"
            disabled={saving || deleting}
            aria-label={`Duplicate attempt ${attempt.id}`}
            onClick={() => onDuplicate(attempt.id)}
          >
            Duplicate
          </button>
        ) : null}
        <button
          type="button"
          className="shot-drawer__btn shot-drawer__btn--danger"
          disabled={deleting}
          aria-label={`Delete attempt ${attempt.id}`}
          onClick={() => onDelete(attempt.id)}
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>

      {expanded ? children : null}
    </article>
  );
}

export function ShotDrawer({
  shot,
  projectId,
  projectAudioAvailable = true,
  onClose,
  onShotUpdated,
}: ShotDrawerProps) {
  const [currentShot, setCurrentShot] = useState<Shot | null>(shot);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [shotNote, setShotNote] = useState("");
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [expandedAttemptId, setExpandedAttemptId] = useState<string | null>(null);
  const [loadingAttempts, setLoadingAttempts] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [deletingAttemptId, setDeletingAttemptId] = useState<string | null>(null);
  const [openSections, setOpenSections] = useState<Record<SectionKey, boolean>>({
    context: true,
    attempts: true,
  });

  const [promptKo, setPromptKo] = useState("");
  const [promptEn, setPromptEn] = useState("");
  const [shotNoteSnapshot, setShotNoteSnapshot] = useState("");
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [systemPromptOpen, setSystemPromptOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [promptSaving, setPromptSaving] = useState(false);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [workflowTemplates, setWorkflowTemplates] = useState<WorkflowTemplate[]>([]);
  const [executionModes, setExecutionModes] = useState<ExecutionMode[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedModeId, setSelectedModeId] = useState("");
  const [renderSaving, setRenderSaving] = useState(false);
  const [renderMessage, setRenderMessage] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  const activeAttempt = useMemo(() => {
    if (!currentShot?.active_attempt_id) return null;
    return attempts.find((attempt) => attempt.id === currentShot.active_attempt_id) ?? null;
  }, [attempts, currentShot?.active_attempt_id]);

  const expandedAttempt = useMemo(() => {
    if (!expandedAttemptId) return null;
    return attempts.find((item) => item.id === expandedAttemptId) ?? null;
  }, [attempts, expandedAttemptId]);

  const selectedWorkflowTemplate = useMemo(
    () =>
      workflowTemplates.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId, workflowTemplates],
  );

  const selectedExecutionMode = useMemo(
    () => executionModes.find((mode) => mode.id === selectedModeId) ?? null,
    [executionModes, selectedModeId],
  );

  const renderDisabledReason = useMemo(() => {
    if (!expandedAttempt) return "Create an attempt before rendering.";
    if (!expandedAttempt.workflow_template_id || !expandedAttempt.execution_mode_id) {
      return "Choose a workflow and mode before rendering.";
    }
    if (selectedWorkflowTemplate?.is_available === false) {
      return "Selected workflow file is missing.";
    }
    const requiredInputs = parseRequiredInputs(selectedExecutionMode);
    if (
      requiredInputs.some((input) => input.includes("image")) &&
      !expandedAttempt.image_relative_path
    ) {
      return "Select a reference image before rendering.";
    }
    if (
      requiredInputs.some((input) => input.startsWith("prompt")) &&
      !expandedAttempt.prompt_ko &&
      !expandedAttempt.prompt_en
    ) {
      return "Add a prompt before rendering.";
    }
    return null;
  }, [expandedAttempt, selectedExecutionMode, selectedWorkflowTemplate?.is_available]);
  const canQueueRender = !renderSaving && renderDisabledReason === null;

  useEffect(() => {
    setCurrentShot(shot);
    setStartTime(shot ? String(shot.start_time) : "");
    setEndTime(shot ? String(shot.end_time) : "");
    setShotNote(shot?.shot_note ?? "");
    setExpandedAttemptId(shot?.active_attempt_id ?? null);
    setError(null);
  }, [shot]);

  useEffect(() => {
    if (!shot) {
      setAttempts([]);
      setExpandedAttemptId(null);
      return;
    }

    let cancelled = false;
    setLoadingAttempts(true);
    setError(null);

    fetchShotAttempts(shot.id)
      .then((data) => {
        if (!cancelled) {
          setAttempts(data);
          const latestAttempt = data.length > 0 ? data[data.length - 1] : null;
          setExpandedAttemptId(shot.active_attempt_id ?? latestAttempt?.id ?? null);
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
    setReviewNote(expandedAttempt?.review_note ?? "");
    setPromptKo(expandedAttempt?.prompt_ko ?? "");
    setPromptEn(expandedAttempt?.prompt_en ?? "");
    setShotNoteSnapshot(expandedAttempt?.shot_note_snapshot ?? currentShot?.shot_note ?? "");
    setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
    setSystemPromptOpen(false);
    setSavedMessage(null);
    setPromptError(null);
    setReviewStatus(null);
    setReviewError(null);
    setVideoUrl(null);
    setVideoError(null);
    setSelectedTemplateId(expandedAttempt?.workflow_template_id ?? "");
    setSelectedModeId(expandedAttempt?.execution_mode_id ?? "");
    setRenderMessage(null);
    setRenderError(null);
  }, [
    expandedAttempt?.id,
    expandedAttempt?.prompt_ko,
    expandedAttempt?.prompt_en,
    expandedAttempt?.review_note,
    expandedAttempt?.shot_note_snapshot,
    expandedAttempt?.workflow_template_id,
    expandedAttempt?.execution_mode_id,
    currentShot?.shot_note,
  ]);

  useEffect(() => {
    if (!expandedAttempt) {
      setWorkflowTemplates([]);
      return;
    }

    let cancelled = false;
    fetchWorkflowTemplates()
      .then((templates) => {
        if (!cancelled) {
          setWorkflowTemplates(templates);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRenderError(err instanceof Error ? err.message : "Failed to load workflows");
          setWorkflowTemplates([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [expandedAttempt?.id]);

  useEffect(() => {
    if (!selectedTemplateId) {
      setExecutionModes([]);
      return;
    }

    let cancelled = false;
    fetchExecutionModes(selectedTemplateId)
      .then((modes) => {
        if (!cancelled) {
          setExecutionModes(modes);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRenderError(err instanceof Error ? err.message : "Failed to load execution modes");
          setExecutionModes([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedTemplateId]);

  if (!currentShot) {
    return null;
  }

  function upsertAttempt(updated: Attempt) {
    setAttempts((items) => {
      const next = items.filter((item) => item.id !== updated.id);
      return [...next, updated].sort((a, b) => a.created_at.localeCompare(b.created_at));
    });
  }

  function setAttemptActiveLocal(attempt: Attempt) {
    setCurrentShot((current) =>
      current
        ? {
            ...current,
            active_attempt_id: attempt.id,
            active_attempt: attempt,
            attempt_count: Math.max(current.attempt_count, attempts.length + 1),
            status: "Needs Input",
          }
        : current,
    );
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

  function selectAttempt(attemptId: string) {
    if (!currentShot) return;
    setExpandedAttemptId(attemptId);
    if (attemptId === currentShot.active_attempt_id) return;
    void saveShotFields({ active_attempt_id: attemptId }, `attempt-${attemptId}`);
  }

  function toggleSection(section: SectionKey) {
    setOpenSections((sections) => ({ ...sections, [section]: !sections[section] }));
  }

  async function handleCreateAttempt() {
    if (!currentShot) return;
    setSaving("new-attempt");
    setError(null);
    try {
      const created = await createAttempt(currentShot.id);
      upsertAttempt(created);
      setExpandedAttemptId(created.id);
      setAttemptActiveLocal(created);
      onShotUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create attempt");
    } finally {
      setSaving(null);
    }
  }

  async function handleDuplicateAttempt(attemptId: string) {
    if (!currentShot) return;
    setSaving(`duplicate-${attemptId}`);
    setError(null);
    try {
      const duplicated = await duplicateAttempt(currentShot.id, attemptId);
      upsertAttempt(duplicated);
      setExpandedAttemptId(duplicated.id);
      setAttemptActiveLocal(duplicated);
      onShotUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to duplicate attempt");
    } finally {
      setSaving(null);
    }
  }

  async function handleAssetSelectedForAttempt(attempt: Attempt, asset: Asset, role: ImageRole) {
    if (!currentShot || attempt.output_metadata) return;
    setSaving(`asset-${role}-${attempt.id}`);
    setError(null);
    try {
      const updated = await saveAttemptRequest(
        currentShot.id,
        attempt.id,
        role === "start"
          ? {
              image_storage_backend: asset.storage_backend,
              image_relative_path: asset.relative_path,
            }
          : {
              end_image_storage_backend: asset.storage_backend,
              end_image_relative_path: asset.relative_path,
            },
      );
      upsertAttempt(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update reference image");
    } finally {
      setSaving(null);
    }
  }

  async function handleClearEndImage(attempt: Attempt) {
    if (!currentShot || attempt.output_metadata) return;
    setSaving(`asset-end-${attempt.id}`);
    setError(null);
    try {
      const updated = await saveAttemptRequest(currentShot.id, attempt.id, {
        end_image_storage_backend: null,
        end_image_relative_path: null,
      });
      upsertAttempt(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to clear end image");
    } finally {
      setSaving(null);
    }
  }

  async function handleGenerate() {
    if (!currentShot || !expandedAttempt || expandedAttempt.output_metadata) return;
    setPromptError(null);
    setSavedMessage(null);
    setGenerating(true);
    try {
      const savedAttempt = await saveAttemptRequest(currentShot.id, expandedAttempt.id, {
        shot_note_snapshot: shotNoteSnapshot,
        prompt_ko: promptKo,
        prompt_en: promptEn,
      });
      upsertAttempt(savedAttempt);
      const updated = await generatePromptRequest(savedAttempt.id, {
        system_prompt: systemPrompt,
      });
      setPromptKo(updated.prompt_ko ?? "");
      setPromptEn(updated.prompt_en ?? "");
      setShotNoteSnapshot(updated.shot_note_snapshot ?? shotNoteSnapshot);
      upsertAttempt(updated);
    } catch (err: unknown) {
      setPromptError(err instanceof Error ? err.message : "Failed to generate prompt");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSavePrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentShot || !expandedAttempt || expandedAttempt.output_metadata) return;
    setPromptError(null);
    setSavedMessage(null);
    setPromptSaving(true);
    try {
      const updated = await saveAttemptRequest(currentShot.id, expandedAttempt.id, {
        shot_note_snapshot: shotNoteSnapshot,
        prompt_ko: promptKo,
        prompt_en: promptEn,
      });
      upsertAttempt(updated);
      setSavedMessage("Prompts saved");
    } catch (err: unknown) {
      setPromptError(err instanceof Error ? err.message : "Failed to save prompts");
    } finally {
      setPromptSaving(false);
    }
  }

  async function handlePlayVideo() {
    if (!currentShot || !expandedAttempt) return;
    setVideoError(null);
    try {
      const url = await fetchVideoUrl(currentShot.id, expandedAttempt.id);
      setVideoUrl(url);
    } catch (err: unknown) {
      setVideoError(err instanceof Error ? err.message : "Failed to load video");
    }
  }

  async function handleSaveRenderSetup() {
    if (!currentShot || !expandedAttempt || expandedAttempt.output_metadata) return;
    setRenderSaving(true);
    setRenderError(null);
    setRenderMessage(null);
    try {
      const updated = await saveAttemptRequest(currentShot.id, expandedAttempt.id, {
        workflow_template_id: selectedTemplateId || null,
        execution_mode_id: selectedModeId || null,
      });
      upsertAttempt(updated);
      setRenderMessage("Render setup saved");
    } catch (err: unknown) {
      setRenderError(err instanceof Error ? err.message : "Failed to save render setup");
    } finally {
      setRenderSaving(false);
    }
  }

  async function handleQueueRender() {
    if (!currentShot || !expandedAttempt) return;
    setRenderSaving(true);
    setRenderError(null);
    setRenderMessage(null);
    try {
      await enqueueRender(currentShot.id, expandedAttempt.id);
      setRenderMessage("Render job queued");
      onShotUpdated();
    } catch (err: unknown) {
      setRenderError(err instanceof Error ? err.message : "Failed to queue render");
    } finally {
      setRenderSaving(false);
    }
  }

  async function handleDeleteAttempt(attemptId: string) {
    if (!currentShot) return;
    setDeletingAttemptId(attemptId);
    setError(null);
    try {
      await deleteAttempt(currentShot.id, attemptId);
      setAttempts((items) => items.filter((item) => item.id !== attemptId));
      setExpandedAttemptId((current) => (current === attemptId ? null : current));
      setCurrentShot((current) => {
        if (!current) return current;
        const nextCount = Math.max(0, current.attempt_count - 1);
        if (current.active_attempt_id === attemptId) {
          return {
            ...current,
            active_attempt_id: null,
            active_attempt: null,
            attempt_count: nextCount,
            status: "Needs Input",
          };
        }
        return { ...current, attempt_count: nextCount };
      });
      onShotUpdated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete attempt");
    } finally {
      setDeletingAttemptId(null);
    }
  }

  async function handleReview(status: ReviewStatus) {
    if (!currentShot || !expandedAttempt) return;
    setReviewError(null);
    setReviewSaving(true);
    try {
      await postReview(currentShot.id, expandedAttempt.id, status);
      setReviewStatus(status);
      setAttempts((items) =>
        items.map((item) =>
          item.id === expandedAttempt.id ? { ...item, status } : item,
        ),
      );
      if (status === "Selected") {
        setCurrentShot((current) =>
          current
            ? {
                ...current,
                active_attempt_id: expandedAttempt.id,
                active_attempt: { ...expandedAttempt, status },
                status,
              }
            : current,
        );
      }
      onShotUpdated();
    } catch (err: unknown) {
      setReviewError(err instanceof Error ? err.message : "Failed to update review");
    } finally {
      setReviewSaving(false);
    }
  }

  async function handleSaveReviewWithNote() {
    if (!currentShot || !expandedAttempt) return;
    setReviewError(null);
    setReviewSaving(true);
    try {
      const status = reviewStatus ?? expandedAttempt.status;
      await postReview(currentShot.id, expandedAttempt.id, status, reviewNote);
      setAttempts((items) =>
        items.map((item) =>
          item.id === expandedAttempt.id ? { ...item, review_note: reviewNote } : item,
        ),
      );
      onShotUpdated();
    } catch (err: unknown) {
      setReviewError(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setReviewSaving(false);
    }
  }

  function renderAttemptEditor(attempt: Attempt) {
    if (!currentShot) return null;
    const locked = Boolean(attempt.output_metadata);
    const idSuffix = attempt.id;
    return (
      <div className="shot-drawer__attempt-editor">
        {locked ? (
          <p className="shot-drawer__locked">
            Rendered attempts are locked. Duplicate this attempt to change inputs.
          </p>
        ) : null}

        <div className="shot-drawer__editor-block">
          <div className="shot-drawer__editor-heading">
            <h4>Reference images</h4>
            <span>Start required, end optional</span>
          </div>
          <div className="shot-drawer__image-slots">
            <div className="shot-drawer__image-slot">
              <div className="shot-drawer__editor-heading">
                <strong>Start image</strong>
                <span>{filenameFromPath(attempt.image_relative_path)}</span>
              </div>
              {locked ? null : (
                <AssetPicker
                  projectId={projectId}
                  shotId={currentShot.id}
                  showCreateAttempt={false}
                  selectLabel={(asset) => `Select start image ${asset.name} for attempt ${attempt.id}`}
                  onAssetSelected={(asset) => {
                    void handleAssetSelectedForAttempt(attempt, asset, "start");
                  }}
                />
              )}
            </div>

            <div className="shot-drawer__image-slot">
              <div className="shot-drawer__editor-heading">
                <strong>End image</strong>
                <span>{filenameFromPath(attempt.end_image_relative_path)}</span>
              </div>
              {locked ? null : (
                <>
                  <AssetPicker
                    projectId={projectId}
                    shotId={currentShot.id}
                    showCreateAttempt={false}
                    selectLabel={(asset) => `Select end image ${asset.name} for attempt ${attempt.id}`}
                    onAssetSelected={(asset) => {
                      void handleAssetSelectedForAttempt(attempt, asset, "end");
                    }}
                  />
                  {attempt.end_image_relative_path ? (
                    <button
                      type="button"
                      className="shot-drawer__btn"
                      aria-label={`Clear end image for attempt ${attempt.id}`}
                      disabled={saving === `asset-end-${attempt.id}`}
                      onClick={() => { void handleClearEndImage(attempt); }}
                    >
                      Clear end image
                    </button>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </div>

        <div className="shot-drawer__editor-block">
          <div className="shot-drawer__section-header">
            <h4>Prompt</h4>
            <button
              type="button"
              className="shot-drawer__action"
              disabled={locked || generating}
              aria-label={`Generate prompt for attempt ${attempt.id}`}
              onClick={() => {
                void handleGenerate();
              }}
            >
              {generating ? "Generating..." : "Generate prompt"}
            </button>
          </div>

          {promptError ? <p className="shot-drawer__error">{promptError}</p> : null}

          <form className="shot-drawer__prompt-form" onSubmit={(event) => { void handleSavePrompt(event); }}>
            <label className="shot-drawer__field" htmlFor={`shot-note-snapshot-${idSuffix}`}>
              <span>Shot note for prompt</span>
              <textarea
                id={`shot-note-snapshot-${idSuffix}`}
                aria-label={`Shot note for prompt for attempt ${attempt.id}`}
                value={shotNoteSnapshot}
                onChange={(event) => setShotNoteSnapshot(event.target.value)}
                rows={4}
                disabled={locked}
              />
            </label>

            <div className="shot-drawer__system-prompt">
              <button
                type="button"
                className="shot-drawer__btn"
                aria-expanded={systemPromptOpen}
                aria-label={`${systemPromptOpen ? "Hide" : "Edit"} system prompt for attempt ${attempt.id}`}
                onClick={() => setSystemPromptOpen((open) => !open)}
              >
                {systemPromptOpen ? "Hide system prompt" : "Edit system prompt"}
              </button>
              {systemPromptOpen ? (
                <label className="shot-drawer__field" htmlFor={`system-prompt-${idSuffix}`}>
                  <span>System prompt</span>
                  <textarea
                    id={`system-prompt-${idSuffix}`}
                    aria-label={`System prompt for attempt ${attempt.id}`}
                    value={systemPrompt}
                    onChange={(event) => setSystemPrompt(event.target.value)}
                    rows={5}
                    disabled={locked}
                  />
                </label>
              ) : null}
            </div>

            <label className="shot-drawer__field" htmlFor={`prompt-ko-${idSuffix}`}>
              <span>Korean prompt</span>
              <textarea
                id={`prompt-ko-${idSuffix}`}
                aria-label={`Korean prompt for attempt ${attempt.id}`}
                value={promptKo}
                onChange={(event) => setPromptKo(event.target.value)}
                rows={7}
                disabled={locked}
              />
            </label>

            <label className="shot-drawer__field" htmlFor={`prompt-en-${idSuffix}`}>
              <span>English prompt</span>
              <textarea
                id={`prompt-en-${idSuffix}`}
                aria-label={`English prompt for attempt ${attempt.id}`}
                value={promptEn}
                onChange={(event) => setPromptEn(event.target.value)}
                rows={7}
                disabled={locked}
              />
            </label>

            <div className="shot-drawer__footer">
              {savedMessage ? <span className="shot-drawer__saved">{savedMessage}</span> : null}
              <button
                type="submit"
                className="shot-drawer__action shot-drawer__action--primary"
                disabled={locked || promptSaving}
              >
                {promptSaving ? "Saving..." : "Save prompts"}
              </button>
            </div>
          </form>
        </div>

        <div className="shot-drawer__editor-block">
          <h4>Workflow</h4>
          <label className="shot-drawer__field" htmlFor={`workflow-template-${idSuffix}`}>
            <span>Workflow Template</span>
            <select
              id={`workflow-template-${idSuffix}`}
              aria-label={`Workflow Template for attempt ${attempt.id}`}
              value={selectedTemplateId}
              disabled={locked}
              onChange={(event) => {
                setSelectedTemplateId(event.target.value);
                setSelectedModeId("");
                setRenderMessage(null);
                setRenderError(null);
              }}
            >
              <option value="">Select workflow</option>
              {workflowTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.is_available ? template.name : `${template.name} (missing)`}
                </option>
              ))}
            </select>
          </label>

          {selectedWorkflowTemplate?.validation_error ? (
            <p className="shot-drawer__error" role="alert">
              {selectedWorkflowTemplate.validation_error}
            </p>
          ) : selectedWorkflowTemplate ? (
            <p className="shot-drawer__muted">
              Workflow ready: {selectedWorkflowTemplate.json_path}
            </p>
          ) : null}

          <label className="shot-drawer__field" htmlFor={`execution-mode-${idSuffix}`}>
            <span>Execution Mode</span>
            <select
              id={`execution-mode-${idSuffix}`}
              aria-label={`Execution Mode for attempt ${attempt.id}`}
              value={selectedModeId}
              disabled={locked || !selectedTemplateId}
              onChange={(event) => {
                setSelectedModeId(event.target.value);
                setRenderMessage(null);
                setRenderError(null);
              }}
            >
              <option value="">Select mode</option>
              {executionModes.map((mode) => (
                <option key={mode.id} value={mode.id}>
                  {mode.name}
                </option>
              ))}
            </select>
          </label>

          {workflowTemplates.length === 0 ? (
            <p className="shot-drawer__muted">No workflow templates configured.</p>
          ) : null}

          {renderDisabledReason ? (
            <p className="shot-drawer__render-reason">{renderDisabledReason}</p>
          ) : null}
          {renderMessage ? <p className="shot-drawer__saved">{renderMessage}</p> : null}
          {renderError ? (
            <p className="shot-drawer__error" role="alert">
              {renderError}
            </p>
          ) : null}

          <div className="shot-drawer__footer">
            <button
              type="button"
              className="shot-drawer__action"
              disabled={locked || renderSaving || !selectedTemplateId || !selectedModeId}
              onClick={() => { void handleSaveRenderSetup(); }}
            >
              {renderSaving ? "Saving..." : "Save render setup"}
            </button>
            <button
              type="button"
              className="shot-drawer__action shot-drawer__action--primary"
              aria-label={`Queue render for attempt ${attempt.id}`}
              disabled={!canQueueRender}
              onClick={() => { void handleQueueRender(); }}
            >
              {renderSaving ? "Queueing..." : "Queue render"}
            </button>
          </div>
        </div>

        <div className="shot-drawer__editor-block">
          <div className="shot-drawer__section-header">
            <h4>Review</h4>
            <button
              className="shot-drawer__btn shot-drawer__btn--play"
              type="button"
              disabled={!attempt.output_metadata}
              onClick={() => void handlePlayVideo()}
            >
              Play video
            </button>
          </div>
          {videoError ? (
            <p className="shot-drawer__error" role="alert">
              {videoError}
            </p>
          ) : null}
          <div className="shot-drawer__status-row" role="group" aria-label={`Review status for attempt ${attempt.id}`}>
            {(["Selected", "Redo", "Rejected"] as ReviewStatus[]).map((status) => (
              <button
                key={status}
                className={`shot-drawer__btn shot-drawer__btn--status${
                  reviewStatus === status ? " shot-drawer__btn--active" : ""
                }`}
                type="button"
                disabled={reviewSaving}
                onClick={() => void handleReview(status)}
                aria-pressed={reviewStatus === status}
              >
                {status}
              </button>
            ))}
          </div>
          <div className="shot-drawer__note-row">
            <label htmlFor={`review-note-${idSuffix}`} className="shot-drawer__label">
              Review Note
            </label>
            <textarea
              id={`review-note-${idSuffix}`}
              className="shot-drawer__textarea"
              aria-label={`Review Note for attempt ${attempt.id}`}
              value={reviewNote}
              onChange={(event) => setReviewNote(event.target.value)}
              rows={4}
              placeholder="Add a review note..."
            />
            <button
              className="shot-drawer__btn shot-drawer__btn--save"
              type="button"
              disabled={reviewSaving}
              onClick={() => void handleSaveReviewWithNote()}
            >
              {reviewSaving ? "Saving..." : "Save note"}
            </button>
          </div>
          {reviewError ? (
            <p className="shot-drawer__error" role="alert">
              {reviewError}
            </p>
          ) : null}
        </div>
      </div>
    );
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

        <section className="shot-drawer__summary" aria-labelledby="active-attempt-summary">
          <div>
            <p className="shot-drawer__eyebrow">Active attempt</p>
            <h3 id="active-attempt-summary" className="shot-drawer__summary-title">
              {activeAttempt ? previewText(activeAttempt.prompt_ko || activeAttempt.prompt_en, 64) : "No attempt selected"}
            </h3>
            <p className="shot-drawer__summary-meta">
              {activeAttempt ? attemptReadiness(activeAttempt) : "Create a new attempt, then fill image, prompt, workflow, and render."}
            </p>
          </div>
        </section>

        <DrawerSection
          id="context"
          title="Shot context"
          open={openSections.context}
          onToggle={toggleSection}
        >
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
            Save time range
          </button>
          <ShotAudioPreview
            projectId={projectId}
            startTime={currentShot.start_time}
            endTime={currentShot.end_time}
            audioAvailable={projectAudioAvailable}
          />
          <div className="shot-drawer__readonly">{currentShot.lyrics_text || "-"}</div>
          <textarea
            className="shot-drawer__textarea"
            aria-label="Shot note"
            value={shotNote}
            onChange={(event) => setShotNote(event.target.value)}
            onBlur={saveShotNote}
            rows={5}
          />
        </DrawerSection>

        <DrawerSection
          id="attempts"
          title="Attempts"
          open={openSections.attempts}
          onToggle={toggleSection}
        >
          <div className="shot-drawer__section-header">
            <p className="shot-drawer__muted">Each attempt owns its image, prompt, workflow, render queue, and review state.</p>
            <button
              type="button"
              className="shot-drawer__action shot-drawer__action--primary"
              disabled={saving === "new-attempt"}
              onClick={() => { void handleCreateAttempt(); }}
            >
              {saving === "new-attempt" ? "Creating..." : "New attempt"}
            </button>
          </div>

          {loadingAttempts ? <p className="shot-drawer__muted">Loading attempts...</p> : null}
          {!loadingAttempts && attempts.length === 0 ? (
            <p className="shot-drawer__muted">No attempts yet.</p>
          ) : null}

          <div className="shot-drawer__attempts">
            {attempts.map((attempt) => (
              <AttemptCard
                key={attempt.id}
                attempt={attempt}
                active={attempt.id === currentShot.active_attempt_id}
                expanded={attempt.id === expandedAttempt?.id}
                saving={
                  saving === `attempt-${attempt.id}` ||
                  saving === `duplicate-${attempt.id}` ||
                  saving === `asset-start-${attempt.id}` ||
                  saving === `asset-end-${attempt.id}` ||
                  reviewSaving
                }
                deleting={deletingAttemptId === attempt.id}
                onToggle={(attemptId) => {
                  setExpandedAttemptId((current) => (current === attemptId ? null : attemptId));
                }}
                onUse={selectAttempt}
                onDuplicate={(attemptId) => { void handleDuplicateAttempt(attemptId); }}
                onDelete={(attemptId) => { void handleDeleteAttempt(attemptId); }}
              >
                {renderAttemptEditor(attempt)}
              </AttemptCard>
            ))}
          </div>
        </DrawerSection>
      </aside>

      <VideoPreviewModal
        videoUrl={videoUrl}
        onClose={() => setVideoUrl(null)}
      />
    </>
  );
}
