import { useEffect, useState } from "react";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { useEngineStore } from "@/stores/useEngineStore";

export function ModelDownloadBanner() {
  const downloading = useEngineStore((s) => s.modelDownloading);
  const progress = useEngineStore((s) => s.modelDownloadProgress);
  const message = useEngineStore((s) => s.modelDownloadMessage);
  const [dismissed, setDismissed] = useState(false);
  const [showReady, setShowReady] = useState(false);

  // When download completes, show "Model ready" briefly then dismiss
  useEffect(() => {
    if (!downloading && progress >= 1 && message === "Model ready") {
      setShowReady(true);
      const timer = setTimeout(() => {
        setShowReady(false);
        setDismissed(true);
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [downloading, progress, message]);

  if (dismissed || (!downloading && !showReady)) return null;

  return (
    <div className="w-full bg-white/[0.03] border-b border-white/[0.07] px-5 py-3 animate-slide-up">
      {showReady ? (
        <div className="flex items-center justify-center gap-2">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse-dot" />
          <span className="text-sm text-white font-medium">Model ready</span>
        </div>
      ) : (
        <div className="flex items-center gap-4 max-w-2xl mx-auto">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-text-primary font-medium">
                Downloading Qwen3-TTS model...
              </span>
              <span className="text-xs text-text-muted">~2 GB</span>
            </div>
            <ProgressBar value={progress} variant="default" />
            <p className="text-xs text-text-muted mt-1">
              {message || "This only happens once"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
