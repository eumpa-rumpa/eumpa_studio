import { useState } from "react";
import type { Project } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ProjectChooser } from "./components/ProjectChooser";
import { QueuePanel } from "./components/QueuePanel";
import { ShotTable } from "./components/ShotTable";

export function App() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  if (selectedProject === null) {
    return <ProjectChooser onSelect={setSelectedProject} />;
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
          <ShotTable projectId={selectedProject.id} />
        </section>
        <QueuePanel />
      </div>
    </AppShell>
  );
}
