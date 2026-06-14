import { useState } from "react";
import type { Project } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ProjectChooser } from "./components/ProjectChooser";

export function App() {
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  if (selectedProject === null) {
    return <ProjectChooser onSelect={setSelectedProject} />;
  }

  return <AppShell />;
}
