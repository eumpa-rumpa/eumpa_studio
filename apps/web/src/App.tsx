import { useEffect, useState } from "react";
import { fetchProject } from "./api/client";
import type { Project, Shot } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ProjectChooser } from "./components/ProjectChooser";
import { QueuePanel } from "./components/QueuePanel";
import { ShotDrawer } from "./components/ShotDrawer";
import { ShotTable } from "./components/ShotTable";
import { WorkflowLibrary } from "./components/WorkflowLibrary";

export function App() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [shotListVersion, setShotListVersion] = useState(0);
  const [queueRefreshKey, setQueueRefreshKey] = useState(0);
  const [restoringProject, setRestoringProject] = useState(true);

  function selectProject(project: Project) {
    window.localStorage.setItem("eumpa-studio:selected-project-id", project.id);
    setSelectedProject(project);
    setSelectedShot(null);
  }

  function switchProject() {
    window.localStorage.removeItem("eumpa-studio:selected-project-id");
    setSelectedProject(null);
    setSelectedShot(null);
  }

  useEffect(() => {
    const storedProjectId = window.localStorage.getItem("eumpa-studio:selected-project-id");
    if (!storedProjectId) {
      setRestoringProject(false);
      return;
    }

    let cancelled = false;
    fetchProject(storedProjectId)
      .then((project) => {
        if (!cancelled) {
          setSelectedProject(project);
          setSelectedShot(null);
        }
      })
      .catch(() => {
        window.localStorage.removeItem("eumpa-studio:selected-project-id");
      })
      .finally(() => {
        if (!cancelled) {
          setRestoringProject(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (selectedProject === null) {
    return (
      <AppShell>
        {restoringProject ? (
          <p className="app-shell__state">Opening last project...</p>
        ) : (
          <ProjectChooser onSelect={selectProject} />
        )}
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="project-workspace">
        <section className="project-workspace__main" aria-labelledby="shots-heading">
          <div className="project-workspace__header">
            <div>
              <p className="project-workspace__eyebrow">Project</p>
              <h2 id="shots-heading" className="project-workspace__title">
                {selectedProject.name}
              </h2>
            </div>
            <button
              type="button"
              className="project-workspace__switch"
              onClick={switchProject}
            >
              Switch project
            </button>
          </div>
          <ShotTable
            key={shotListVersion}
            projectId={selectedProject.id}
            onShotSelect={setSelectedShot}
            onJobsUpdated={() => setQueueRefreshKey((key) => key + 1)}
          />
        </section>
        <aside className="project-workspace__side" aria-label="Project operations">
          <WorkflowLibrary refreshKey={shotListVersion} />
          <QueuePanel refreshKey={queueRefreshKey} />
        </aside>
      </div>
      <ShotDrawer
        shot={selectedShot}
        projectId={selectedProject.id}
        projectAudioAvailable={Boolean(selectedProject.audio_relative_path)}
        onClose={() => setSelectedShot(null)}
        onShotUpdated={() => setShotListVersion((version) => version + 1)}
      />
    </AppShell>
  );
}
