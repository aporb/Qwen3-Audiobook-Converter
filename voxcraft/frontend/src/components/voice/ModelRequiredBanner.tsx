import { useEffect, useState } from "react";
import { Button } from "@/components/shared/Button";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { useEngineStore } from "@/stores/useEngineStore";

interface ModelRequiredBannerProps {
  voiceMode: string;
}

export function ModelRequiredBanner({ voiceMode }: ModelRequiredBannerProps) {
  const [cached, setCached] = useState<boolean | null>(null);
  const checkModelCached = useEngineStore((s) => s.checkModelCached);
  const preloadModel = useEngineStore((s) => s.preloadModel);
  const downloading = useEngineStore((s) => s.modelDownloading);
  const downloadProgress = useEngineStore((s) => s.modelDownloadProgress);
  const downloadMessage = useEngineStore((s) => s.modelDownloadMessage);

  useEffect(() => {
    checkModelCached(voiceMode).then(setCached);
  }, [voiceMode, checkModelCached]);

  // Model is cached or still checking
  if (cached === null || cached === true) {
    if (cached === true) {
      return (
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
          <span className="text-xs text-text-muted">Model ready</span>
        </div>
      );
    }
    return null;
  }

  // Downloading
  if (downloading) {
    return (
      <div className="p-3 rounded-lg border border-glass-border bg-surface mb-2">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm text-text-primary font-medium">Downloading model...</span>
          <span className="text-xs text-text-muted">~3.5 GB</span>
        </div>
        <ProgressBar value={downloadProgress} variant="local" />
        <p className="text-xs text-text-muted mt-1">
          {downloadMessage || "This only happens once per voice mode"}
        </p>
      </div>
    );
  }

  // Not cached — show download prompt
  return (
    <div className="p-3 rounded-lg border border-white/10 bg-white/[0.03] mb-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-text-primary">
            {voiceMode === "voice_design" ? "Voice Design" : "Voice Clone"} model required
          </p>
          <p className="text-xs text-text-muted mt-0.5">~3.5 GB download, stored locally</p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => {
            preloadModel(voiceMode);
          }}
        >
          Download
        </Button>
      </div>
    </div>
  );
}
