import { useRef, useState } from "react";
import type { Project } from "../api/types";
import { useProjects } from "../hooks/useProjects";

interface ProjectChooserProps {
  onSelect: (project: Project) => void;
}

export function ProjectChooser({ onSelect }: ProjectChooserProps) {
  const { projects, loading, error, create } = useProjects();

  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const audioRef = useRef<HTMLInputElement>(null);
  const lyricsFileRef = useRef<HTMLInputElement>(null);
  const visualBibleFileRef = useRef<HTMLInputElement>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    const formData = new FormData();
    formData.append("name", name.trim());

    const audioFile = audioRef.current?.files?.[0];
    if (audioFile) formData.append("audio", audioFile);

    const lyricsFile = lyricsFileRef.current?.files?.[0];
    if (lyricsFile) formData.append("lyrics_file", lyricsFile);

    const visualBibleFile = visualBibleFileRef.current?.files?.[0];
    if (visualBibleFile) formData.append("visual_bible_file", visualBibleFile);

    setCreating(true);
    setCreateError(null);
    try {
      const project = await create(formData);
      onSelect(project);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create project");
      setCreating(false);
    }
  }

  return (
    <div className="project-chooser">
      <h2 className="project-chooser__heading">Create a Project</h2>

      <form className="project-chooser__form" onSubmit={(e) => { void handleCreate(e); }}>
        <div className="project-chooser__field">
          <label htmlFor="project-name">Project name</label>
          <input
            id="project-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="My Music Video"
          />
        </div>

        <div className="project-chooser__field">
          <label htmlFor="project-audio">Audio file (optional)</label>
          <input
            id="project-audio"
            type="file"
            accept="audio/*"
            ref={audioRef}
          />
        </div>

        <div className="project-chooser__field">
          <label htmlFor="project-lyrics-file">Lyrics file (optional)</label>
          <input
            id="project-lyrics-file"
            type="file"
            accept=".txt,.lrc,.srt"
            ref={lyricsFileRef}
          />
        </div>

        <div className="project-chooser__field">
          <label htmlFor="project-visual-bible">Visual bible file (optional)</label>
          <input
            id="project-visual-bible"
            type="file"
            accept=".txt,.md,.pdf"
            ref={visualBibleFileRef}
          />
        </div>

        {createError && (
          <p className="project-chooser__error">{createError}</p>
        )}

        <button
          type="submit"
          disabled={creating || !name.trim()}
          className="project-chooser__submit"
        >
          {creating ? "Creating..." : "Create project"}
        </button>
      </form>

      {(loading || projects.length > 0) && (
        <div className="project-chooser__existing">
          <h2 className="project-chooser__heading">Open Existing Project</h2>

          {error && <p className="project-chooser__error">{error}</p>}

          {loading ? (
            <p>Loading projects...</p>
          ) : (
            <ul className="project-chooser__list">
              {projects.map((project) => (
                <li key={project.id} className="project-chooser__item">
                  <button
                    type="button"
                    className="project-chooser__open-btn"
                    onClick={() => onSelect(project)}
                  >
                    {project.name}
                    <span className="project-chooser__date">
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
