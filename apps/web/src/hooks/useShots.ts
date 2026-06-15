import { useCallback, useEffect, useState } from "react";
import { fetchShots } from "../api/client";
import type { Shot } from "../api/types";

const POLL_INTERVAL_MS = 5000;

interface UseShotsResult {
  shots: Shot[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useShots(projectId: string): UseShotsResult {
  const [shots, setShots] = useState<Shot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const loadShots = useCallback(
    async (cancelled: () => boolean) => {
      if (!projectId) {
        setShots([]);
        setLoading(false);
        return;
      }

      try {
        const data = await fetchShots(projectId);
        if (!cancelled()) {
          setShots(data);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!cancelled()) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setLoading(false);
        }
      }
    },
    [projectId],
  );

  useEffect(() => {
    let cancelled = false;
    const isCancelled = () => cancelled;

    setLoading(true);
    void loadShots(isCancelled);

    const intervalId = window.setInterval(() => {
      void loadShots(isCancelled);
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [loadShots, reloadTick]);

  const refetch = useCallback(() => {
    setReloadTick((tick) => tick + 1);
  }, []);

  return { shots, loading, error, refetch };
}
