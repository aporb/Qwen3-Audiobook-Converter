import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/shared/Button";
import { Badge } from "@/components/shared/Badge";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { useCleaningStore } from "@/stores/useCleaningStore";
import { useWebLLM } from "@/hooks/useWebLLM";
import { BROWSER_MODELS } from "@/lib/cleaning-presets";

export function BrowserModelManager() {
  const browserModelId = useCleaningStore((s) => s.browserModelId);
  const setBrowserModelId = useCleaningStore((s) => s.setBrowserModelId);
  const setBrowserModelReady = useCleaningStore((s) => s.setBrowserModelReady);
  const setBrowserModelDownloading = useCleaningStore((s) => s.setBrowserModelDownloading);
  const setBrowserModelProgress = useCleaningStore((s) => s.setBrowserModelProgress);

  const { loadModel, isReady, isDownloading, downloadProgress, downloadText, loadError, webgpuAvailable } =
    useWebLLM();

  const [cacheCleared, setCacheCleared] = useState(false);

  const handleLoadModel = useCallback(() => {
    setBrowserModelDownloading(true);
    setBrowserModelReady(false);
    setCacheCleared(false);
    loadModel(browserModelId);
  }, [browserModelId, loadModel, setBrowserModelDownloading, setBrowserModelReady]);

  const handleClearCache = useCallback(async () => {
    const names = await caches.keys();
    let cleared = 0;
    for (const name of names) {
      if (name.includes("webllm") || name.includes("mlc") || name.includes("huggingface")) {
        await caches.delete(name);
        cleared++;
      }
    }
    if (cleared === 0) {
      // Fallback: clear all caches for this origin
      for (const name of names) {
        await caches.delete(name);
      }
    }
    setCacheCleared(true);
  }, []);

  // Sync hook state to store for cross-component access
  useEffect(() => {
    if (isReady) {
      setBrowserModelReady(true);
      setBrowserModelDownloading(false);
    }
  }, [isReady, setBrowserModelReady, setBrowserModelDownloading]);

  useEffect(() => {
    if (isDownloading) {
      setBrowserModelProgress(downloadProgress);
    }
  }, [isDownloading, downloadProgress, setBrowserModelProgress]);

  const selectedModel = BROWSER_MODELS.find((m) => m.id === browserModelId);
  const isQuotaError = loadError?.toLowerCase().includes("quota");

  return (
    <div className="flex flex-col gap-2">
      {/* WebGPU check */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">WebGPU</span>
        <Badge variant={webgpuAvailable ? "active" : "inactive"} dot>
          {webgpuAvailable ? "Available" : "Not available"}
        </Badge>
      </div>

      {!webgpuAvailable && (
        <p className="text-xs text-red-400">
          WebGPU is not supported in this browser. Try Chrome 113+ or Edge 113+.
        </p>
      )}

      {webgpuAvailable && (
        <>
          {/* Model selector */}
          <select
            value={browserModelId}
            onChange={(e) => setBrowserModelId(e.target.value)}
            disabled={isDownloading}
            className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary"
          >
            {BROWSER_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label} ({m.size})
              </option>
            ))}
          </select>

          {selectedModel && (
            <p className="text-xs text-text-muted">{selectedModel.description}</p>
          )}

          {/* Download / status */}
          {!isReady && !isDownloading && (
            <Button variant="secondary" size="sm" onClick={handleLoadModel}>
              {cacheCleared ? "Retry Download & Load" : `Download & Load Model (${selectedModel?.size ?? "..."})`}
            </Button>
          )}

          {isDownloading && (
            <div className="flex flex-col gap-1">
              <ProgressBar value={downloadProgress} label={downloadText} variant="default" />
            </div>
          )}

          {isReady && (
            <Badge variant="active" dot>Ready</Badge>
          )}

          {/* Load error display */}
          {loadError && !isDownloading && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs text-red-400">Load failed: {loadError}</p>
              {isQuotaError && (
                <>
                  <p className="text-xs text-text-muted">
                    Browser storage is full from previous downloads. Clear the cache and try again.
                  </p>
                  <Button variant="ghost" size="sm" onClick={handleClearCache}>
                    {cacheCleared ? "Cache Cleared — Click Retry Above" : "Clear Model Cache"}
                  </Button>
                </>
              )}
            </div>
          )}

          {/* Hint when model not loaded and no error */}
          {!isReady && !isDownloading && !loadError && (
            <p className="text-xs text-amber-400">
              Model must be loaded each session. Click above to load.
            </p>
          )}
        </>
      )}
    </div>
  );
}
