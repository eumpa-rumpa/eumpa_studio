import { useCallback, useEffect, useRef, useState } from "react";
import type { Asset, Attempt } from "../api/types";

interface AssetPickerProps {
  projectId: string;
  shotId: string | null;
  onAssetSelected?: (asset: Asset) => void;
  onAttemptCreated?: (attempt: Attempt) => void;
  selectLabel?: (asset: Asset) => string;
  showCreateAttempt?: boolean;
}

async function fetchAssets(projectId: string): Promise<Asset[]> {
  const response = await fetch(`/api/assets/${projectId}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<Asset[]>;
}

async function uploadAsset(projectId: string, file: File): Promise<Asset> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`/api/assets/${projectId}`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<Asset>;
}

async function useAssetForShot(
  projectId: string,
  assetId: string,
  shotId: string,
): Promise<Attempt> {
  const response = await fetch(
    `/api/assets/${projectId}/${assetId}/use-for-shot/${shotId}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<Attempt>;
}

export function AssetPicker({
  projectId,
  shotId,
  onAssetSelected,
  onAttemptCreated,
  selectLabel,
  showCreateAttempt = true,
}: AssetPickerProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadAssets = useCallback(() => {
    setLoading(true);
    fetchAssets(projectId)
      .then((data) => {
        setAssets(data);
        setError(null);
        setLoading(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load assets");
        setLoading(false);
      });
  }, [projectId]);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    try {
      await uploadAsset(projectId, file);
      loadAssets();
    } catch (err: unknown) {
      setUploadError(
        err instanceof Error ? err.message : "Failed to upload asset",
      );
    } finally {
      setUploading(false);
      // Reset so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleAssetClick(asset: Asset) {
    setSelectedAsset(asset);
    onAssetSelected?.(asset);
  }

  async function handleCreateAttempt(asset: Asset) {
    setActionError(null);
    if (shotId) {
      try {
        const attempt = await useAssetForShot(projectId, asset.id, shotId);
        onAttemptCreated?.(attempt);
      } catch (err: unknown) {
        setActionError(
          err instanceof Error ? err.message : "Failed to assign asset to shot",
        );
        return;
      }
    }
  }

  return (
    <div className="asset-picker">
      <div className="asset-picker__toolbar">
        <button
          type="button"
          className="asset-picker__upload-btn"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? "Uploading..." : "Upload image"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => { void handleUpload(e); }}
        />
      </div>

      {uploadError && (
        <p className="asset-picker__error">{uploadError}</p>
      )}
      {actionError && (
        <p className="asset-picker__error">{actionError}</p>
      )}

      {loading ? (
        <p className="asset-picker__status">Loading assets...</p>
      ) : error ? (
        <p className="asset-picker__error">{error}</p>
      ) : assets.length === 0 ? (
        <p className="asset-picker__status">No assets yet. Upload an image to get started.</p>
      ) : (
        <ul className="asset-picker__grid">
          {assets.map((asset) => (
            <li key={asset.id} className="asset-picker__item">
              <button
                type="button"
                className={
                  selectedAsset?.id === asset.id
                    ? "asset-picker__thumb-btn asset-picker__thumb-btn--selected"
                    : "asset-picker__thumb-btn"
                }
                onClick={() => handleAssetClick(asset)}
                title={asset.name}
                aria-label={selectLabel ? selectLabel(asset) : `Select asset ${asset.name}`}
              >
                <img
                  src={asset.thumb_url}
                  alt={asset.name}
                  className="asset-picker__thumb"
                />
                <span className="asset-picker__label">{asset.name}</span>
              </button>
              {selectedAsset?.id === asset.id && shotId && showCreateAttempt ? (
                <button
                  type="button"
                  className="asset-picker__create-btn"
                  onClick={() => {
                    void handleCreateAttempt(asset);
                  }}
                >
                  Create attempt from {asset.name}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
