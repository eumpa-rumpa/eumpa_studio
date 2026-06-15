import { useState } from "react";
import type { Project, Shot } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ProjectChooser } from "./components/ProjectChooser";
import { QueuePanel } from "./components/QueuePanel";
import { ShotDrawer } from "./components/ShotDrawer";
import { ShotTable } from "./components/ShotTable";

export function App() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [selectedShot, setSelectedShot] = useState<Shot | null>(null);
  const [shotListVersion, setShotListVersion] = useState(0);

  if (selectedProject === null) {
    return (
      <ProjectChooser
        onSelect={(project) => {
          setSelectedProject(project);
          setSelectedShot(null);
        }}
      />
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
          </div>
          <ShotTable
            key={shotListVersion}
            projectId={selectedProject.id}
            onShotSelect={setSelectedShot}
          />
        </section>
        <QueuePanel />
      </div>
      <ShotDrawer
        shot={selectedShot}
        projectId={selectedProject.id}
        onClose={() => setSelectedShot(null)}
        onShotUpdated={() => setShotListVersion((version) => version + 1)}
      />
    </AppShell>
  );
}
