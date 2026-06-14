import { useEffect, useMemo, useState } from "react";
import { fetchJobs } from "../api/client";
import type { Job } from "../api/types";

const POLL_INTERVAL_MS = 3000;

interface UseJobsResult {
  running: Job | null;
  pending: Job[];
  all: Job[];
  error: string | null;
  loading: boolean;
}

export function useJobs(): UseJobsResult {
  const [all, setAll] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      try {
        const jobs = await fetchJobs();
        if (!cancelled) {
          setAll(jobs);
          setError(null);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    void loadJobs();
    const intervalId = window.setInterval(() => {
      void loadJobs();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return useMemo(
    () => ({
      running: all.find((job) => job.status === "running") ?? null,
      pending: all.filter((job) => job.status === "pending"),
      all,
      error,
      loading,
    }),
    [all, error, loading],
  );
}
