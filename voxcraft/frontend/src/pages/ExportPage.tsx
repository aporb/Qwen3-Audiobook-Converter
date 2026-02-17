import { useParams } from "react-router-dom";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { ExportPanel } from "@/components/export/ExportPanel";
import { useTTSStore } from "@/stores/useTTSStore";

export function ExportPage() {
  const { projectId } = useParams();
  const audioUrl = useTTSStore((s) => s.audioUrl);
  const sourceText = useTTSStore((s) => s.sourceText);
  const audioDuration = useTTSStore((s) => s.audioDuration);

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Export</h1>
        <p className="text-sm text-text-secondary mt-1">
          Download your audio in different formats.
          {projectId && (
            <span className="text-text-muted"> Project: {projectId}</span>
          )}
        </p>
      </div>

      {audioUrl ? (
        <ExportPanel
          audioUrl={audioUrl}
          sourceText={sourceText}
          audioDuration={audioDuration}
        />
      ) : (
        <GlassPanel solid className="text-center py-12">
          <p className="text-text-secondary">
            No audio to export yet. Generate audio first in Quick Clip or Audiobook.
          </p>
        </GlassPanel>
      )}
    </div>
  );
}
