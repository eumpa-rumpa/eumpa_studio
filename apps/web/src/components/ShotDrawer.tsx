import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { Attempt } from "../api/types";
import { usePrompt } from "../hooks/usePrompt";

interface ShotDrawerProps {
  attempt: Attempt | null;
  open?: boolean;
  title?: string;
  onClose?: () => void;
  onAttemptChange?: (attempt: Attempt) => void;
}

export function ShotDrawer({
  attempt,
  open = true,
  title = "Shot Details",
  onClose,
  onAttemptChange,
}: ShotDrawerProps) {
  const {
    attempt: generatedAttempt,
    generating,
    saving,
    error,
    generatePrompt,
    savePrompt,
  } = usePrompt(attempt?.id ?? null, attempt?.shot_id ?? null);

  const activeAttempt = useMemo(
    () => generatedAttempt ?? attempt,
    [attempt, generatedAttempt],
  );
  const [promptKo, setPromptKo] = useState("");
  const [promptEn, setPromptEn] = useState("");
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    setPromptKo(activeAttempt?.prompt_ko ?? "");
    setPromptEn(activeAttempt?.prompt_en ?? "");
    setSavedMessage(null);
  }, [activeAttempt?.id, activeAttempt?.prompt_ko, activeAttempt?.prompt_en]);

  async function handleGenerate() {
    setSavedMessage(null);
    try {
      const updated = await generatePrompt();
      onAttemptChange?.(updated);
    } catch {
      // usePrompt exposes the error message for rendering.
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavedMessage(null);
    try {
      const updated = await savePrompt(promptKo, promptEn);
      onAttemptChange?.(updated);
      setSavedMessage("Prompts saved");
    } catch {
      // usePrompt exposes the error message for rendering.
    }
  }

  if (!open) {
    return null;
  }

  return (
    <aside className="shot-drawer" aria-labelledby="shot-drawer-title">
      <div className="shot-drawer__header">
        <div>
          <p className="shot-drawer__eyebrow">Attempt</p>
          <h2 id="shot-drawer-title" className="shot-drawer__title">
            {title}
          </h2>
        </div>
        {onClose ? (
          <button
            type="button"
            className="shot-drawer__close"
            onClick={onClose}
            aria-label="Close drawer"
          >
            x
          </button>
        ) : null}
      </div>

      <section className="shot-drawer__section" aria-labelledby="prompt-section-title">
        <div className="shot-drawer__section-header">
          <h3 id="prompt-section-title">Prompt</h3>
          <button
            type="button"
            className="shot-drawer__action"
            disabled={activeAttempt === null || generating}
            onClick={() => { void handleGenerate(); }}
          >
            {generating ? (
              <>
                <span className="shot-drawer__spinner" aria-hidden="true" />
                Generating...
              </>
            ) : (
              "Generate Prompt"
            )}
          </button>
        </div>

        {error ? <p className="shot-drawer__error">{error}</p> : null}

        {activeAttempt === null ? (
          <p className="shot-drawer__empty">Select an attempt to generate prompts.</p>
        ) : (
          <form className="shot-drawer__prompt-form" onSubmit={(event) => { void handleSave(event); }}>
            <label className="shot-drawer__field" htmlFor="prompt-ko">
              <span>Korean prompt</span>
              <textarea
                id="prompt-ko"
                value={promptKo}
                onChange={(event) => setPromptKo(event.target.value)}
                rows={10}
              />
            </label>

            <label className="shot-drawer__field" htmlFor="prompt-en">
              <span>English prompt</span>
              <textarea
                id="prompt-en"
                value={promptEn}
                onChange={(event) => setPromptEn(event.target.value)}
                rows={10}
              />
            </label>

            <div className="shot-drawer__footer">
              {savedMessage ? <span className="shot-drawer__saved">{savedMessage}</span> : null}
              <button
                type="submit"
                className="shot-drawer__action shot-drawer__action--primary"
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Prompts"}
              </button>
            </div>
          </form>
        )}
      </section>
    </aside>
  );
}
