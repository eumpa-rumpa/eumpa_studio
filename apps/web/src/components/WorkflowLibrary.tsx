import { useEffect, useState } from "react";
import {
  bootstrapLtxLipSyncWorkflow,
  fetchWorkflowTemplates,
} from "../api/client";
import type { WorkflowTemplate } from "../api/types";

interface WorkflowLibraryProps {
  refreshKey?: number;
}

export function WorkflowLibrary({ refreshKey = 0 }: WorkflowLibraryProps) {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadTemplates() {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchWorkflowTemplates();
      setTemplates(items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTemplates();
  }, [refreshKey]);

  async function handleBootstrap() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await bootstrapLtxLipSyncWorkflow();
      setMessage(`${result.template.name} ready`);
      await loadTemplates();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add workflow");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workflow-library" aria-labelledby="workflow-library-heading">
      <div className="workflow-library__header">
        <div>
          <p className="workflow-library__eyebrow">Workflows</p>
          <h2 id="workflow-library-heading" className="workflow-library__title">
            Workflow Library
          </h2>
        </div>
        <button
          type="button"
          className="workflow-library__button"
          disabled={saving}
          onClick={() => {
            void handleBootstrap();
          }}
        >
          {saving ? "Adding..." : "Add skill LTX workflow"}
        </button>
      </div>

      {message ? <p className="workflow-library__message">{message}</p> : null}
      {error ? (
        <p className="workflow-library__error" role="alert">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="workflow-library__empty">Loading workflows...</p>
      ) : templates.length === 0 ? (
        <p className="workflow-library__empty">No workflows configured.</p>
      ) : (
        <ul className="workflow-library__list" aria-label="Workflow templates">
          {templates.map((template) => (
            <li key={template.id} className="workflow-library__item">
              <span className="workflow-library__name">{template.name}</span>
              <span
                className={
                  template.is_available
                    ? "workflow-library__status workflow-library__status--ready"
                    : "workflow-library__status workflow-library__status--blocked"
                }
              >
                {template.is_available ? "Ready" : "Missing"}
              </span>
              <code className="workflow-library__path">{template.json_path}</code>
              {template.validation_error ? (
                <span className="workflow-library__detail">
                  {template.validation_error}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
