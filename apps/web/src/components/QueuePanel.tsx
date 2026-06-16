import type { Job } from "../api/types";
import { useJobs } from "../hooks/useJobs";

function describeJob(job: Job): string {
  const target = job.target_entity_id ?? job.target_entity_type ?? "untargeted";
  return `${job.type} ${target}`;
}

interface QueuePanelProps {
  refreshKey?: number;
}

export function QueuePanel({ refreshKey = 0 }: QueuePanelProps) {
  const { running, pending, error, loading } = useJobs(refreshKey);

  return (
    <section className="queue-panel" aria-labelledby="queue-panel-title">
      <div className="queue-panel__header">
        <div>
          <p className="queue-panel__eyebrow">Job Queue</p>
          <h2 id="queue-panel-title" className="queue-panel__title">
            Background execution
          </h2>
        </div>
        <span className="queue-panel__count">Pending: {pending.length} jobs</span>
      </div>

      <div className="queue-panel__running">
        <span className="queue-panel__label">Running:</span>
        <strong>{running ? describeJob(running) : loading ? "Checking queue" : "None"}</strong>
      </div>

      {error ? <p className="queue-panel__error">{error}</p> : null}

      <div className="queue-panel__pending" aria-label="Pending jobs">
        {pending.length === 0 ? (
          <p className="queue-panel__empty">No pending jobs</p>
        ) : (
          <ul className="queue-panel__list">
            {pending.map((job) => (
              <li key={job.id} className="queue-panel__item">
                <span>{job.type}</span>
                <code>{job.target_entity_id ?? job.target_entity_type ?? "untargeted"}</code>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
