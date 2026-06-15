import { useCallback, useEffect, useState } from "react";
import {
  generatePrompt as generatePromptRequest,
  savePrompt as savePromptRequest,
} from "../api/client";
import type { Attempt } from "../api/types";

interface UsePromptResult {
  attempt: Attempt | null;
  generating: boolean;
  saving: boolean;
  error: string | null;
  generatePrompt: () => Promise<Attempt>;
  savePrompt: (promptKo: string, promptEn: string) => Promise<Attempt>;
}

export function usePrompt(
  attemptId: string | null,
  shotId: string | null = null,
): UsePromptResult {
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAttempt(null);
    setError(null);
  }, [attemptId]);

  const generatePrompt = useCallback(async (): Promise<Attempt> => {
    if (attemptId === null) {
      throw new Error("Select an attempt before generating prompts");
    }

    setGenerating(true);
    setError(null);
    try {
      const updated = await generatePromptRequest(attemptId);
      setAttempt(updated);
      return updated;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to generate prompt";
      setError(message);
      throw err;
    } finally {
      setGenerating(false);
    }
  }, [attemptId]);

  const savePrompt = useCallback(
    async (promptKo: string, promptEn: string): Promise<Attempt> => {
      if (attemptId === null) {
        throw new Error("Select an attempt before saving prompts");
      }

      const resolvedShotId = shotId ?? attempt?.shot_id;
      if (resolvedShotId === null || resolvedShotId === undefined) {
        throw new Error("Shot id is required before saving prompts");
      }

      setSaving(true);
      setError(null);
      try {
        const updated = await savePromptRequest(resolvedShotId, attemptId, {
          prompt_ko: promptKo,
          prompt_en: promptEn,
        });
        setAttempt(updated);
        return updated;
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Failed to save prompts";
        setError(message);
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [attempt?.shot_id, attemptId, shotId],
  );

  return {
    attempt,
    generating,
    saving,
    error,
    generatePrompt,
    savePrompt,
  };
}
