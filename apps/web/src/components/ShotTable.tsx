import type { Shot } from "../api/types";
import { useShots } from "../hooks/useShots";

interface ShotTableProps {
  projectId: string;
  onShotSelect?: (shot: Shot) => void;
}

function previewText(value: string | null, maxLength: number): string {
  if (!value) return "—";
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

function formatSeconds(value: number): string {
  return value.toFixed(1).replace(/\.0$/, "");
}

export function ShotTable({ projectId, onShotSelect }: ShotTableProps) {
  const { shots, loading, error } = useShots(projectId);

  if (loading) {
    return <p className="shot-table__state">Loading shots...</p>;
  }

  if (error) {
    return <p className="shot-table__state shot-table__state--error">{error}</p>;
  }

  if (shots.length === 0) {
    return <p className="shot-table__state">No shots yet. Run alignment to generate shots.</p>;
  }

  return (
    <div className="shot-table" aria-label="Shot production table">
      <table className="shot-table__table">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Time</th>
            <th scope="col">Speaker</th>
            <th scope="col">Lyrics</th>
            <th scope="col">Shot Note</th>
            <th scope="col">Attempts</th>
            <th scope="col">Status</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {shots.map((shot) => (
            <tr key={shot.id}>
              <td className="shot-table__index">{shot.order + 1}</td>
              <td className="shot-table__time">
                {formatSeconds(shot.start_time)}-{formatSeconds(shot.end_time)}s
              </td>
              <td>{shot.speaker ?? "—"}</td>
              <td className="shot-table__preview">{previewText(shot.lyrics_text, 60)}</td>
              <td className="shot-table__preview">{previewText(shot.shot_note, 40)}</td>
              <td>
                <span className="shot-table__badge">{shot.attempt_count}</span>
              </td>
              <td>
                <span className="shot-table__status">{shot.status}</span>
              </td>
              <td>
                <button
                  type="button"
                  className="shot-table__open"
                  onClick={() => onShotSelect?.(shot)}
                >
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
