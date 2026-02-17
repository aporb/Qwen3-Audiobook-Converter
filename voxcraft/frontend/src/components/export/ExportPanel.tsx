import { useState } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { Toggle } from "@/components/shared/Toggle";
import { FormatSelector } from "./FormatSelector";
import { apiFetch } from "@/lib/api";

interface ExportPanelProps {
  audioUrl: string | null;
  sourceText?: string | null;
  audioDuration?: number | null;
}

export function ExportPanel({ audioUrl, sourceText, audioDuration }: ExportPanelProps) {
  const [format, setFormat] = useState("wav");
  const [includeSrt, setIncludeSrt] = useState(false);
  const [includeVtt, setIncludeVtt] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!audioUrl) return null;

  // Extract file_id from audio URL: "/api/audio/files/{file_id}"
  const fileId = audioUrl.split("/").pop() ?? "";

  const handleDownloadAudio = async () => {
    setIsExporting(true);
    setError(null);
    try {
      if (format === "wav") {
        // Direct download — no conversion needed
        window.open(audioUrl, "_blank");
      } else {
        const res = await apiFetch<{ download_url: string }>("/export/convert-format", {
          method: "POST",
          body: JSON.stringify({ file_id: fileId, output_format: format }),
        });
        window.open(`/api${res.download_url}`, "_blank");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadSubtitles = async (fmt: "srt" | "vtt") => {
    if (!sourceText || !audioDuration) return;
    setError(null);
    try {
      const res = await apiFetch<{ download_url: string }>("/export/subtitles", {
        method: "POST",
        body: JSON.stringify({
          file_id: fileId,
          text: sourceText,
          duration_seconds: audioDuration,
          format: fmt,
        }),
      });
      window.open(`/api${res.download_url}`, "_blank");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <GlassPanel solid className="animate-slide-up">
      <h3 className="text-sm font-semibold text-text-primary mb-4">Export</h3>

      <div className="flex flex-col gap-4">
        <FormatSelector value={format} onChange={setFormat} />

        {sourceText && audioDuration && audioDuration > 0 && (
          <div className="flex flex-col gap-2">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              Subtitles
            </h4>
            <div className="flex items-center gap-3">
              <Toggle checked={includeSrt} onChange={setIncludeSrt} label="SRT subtitles" />
              {includeSrt && (
                <button
                  onClick={() => handleDownloadSubtitles("srt")}
                  className="text-xs text-white/60 hover:text-white transition-colors"
                >
                  Download .srt
                </button>
              )}
            </div>
            <div className="flex items-center gap-3">
              <Toggle checked={includeVtt} onChange={setIncludeVtt} label="WebVTT subtitles" />
              {includeVtt && (
                <button
                  onClick={() => handleDownloadSubtitles("vtt")}
                  className="text-xs text-white/60 hover:text-white transition-colors"
                >
                  Download .vtt
                </button>
              )}
            </div>
          </div>
        )}

        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}

        <div className="flex gap-2">
          <Button
            variant="primary"
            size="md"
            className="w-full"
            loading={isExporting}
            onClick={handleDownloadAudio}
          >
            Download {format.toUpperCase()}
          </Button>
        </div>
      </div>
    </GlassPanel>
  );
}
