interface VideoPreviewModalProps {
  videoUrl: string | null;
  onClose: () => void;
}

export function VideoPreviewModal({ videoUrl, onClose }: VideoPreviewModalProps) {
  if (!videoUrl) return null;

  return (
    <div
      className="video-modal__overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Video preview"
      onClick={onClose}
    >
      <div
        className="video-modal__content"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="video-modal__close"
          aria-label="Close video preview"
          onClick={onClose}
          type="button"
        >
          ✕
        </button>
        <video
          className="video-modal__video"
          src={videoUrl}
          controls
          autoPlay
        />
      </div>
    </div>
  );
}
