import { useCallback, useEffect, useState } from "react";
import {
  createProject,
  fetchProject,
  fetchProjects,
} from "../api/client";
import type { Project } from "../api/types";

interface UseProjectsResult {
  projects: Project[];
  loading: boolean;
  error: string | null;
  create: (formData: FormData) => Promise<Project>;
  get: (id: string) => Promise<Project>;
  reload: () => void;
}

export function useProjects(): UseProjectsResult {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchProjects()
      .then((data) => {
        if (!cancelled) {
          setProjects(data);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [reloadTick]);

  const reload = useCallback(() => {
    setReloadTick((t) => t + 1);
  }, []);

  const create = useCallback(async (formData: FormData): Promise<Project> => {
    const project = await createProject(formData);
    setReloadTick((t) => t + 1);
    return project;
  }, []);

  const get = useCallback(async (id: string): Promise<Project> => {
    return fetchProject(id);
  }, []);

  return { projects, loading, error, create, get, reload };
}
