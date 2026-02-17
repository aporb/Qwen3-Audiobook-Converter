import { GlassPanel } from "@/components/shared/GlassPanel";
import { useCleaningStore } from "@/stores/useCleaningStore";

export function CleaningPreview() {
  const previewOriginal = useCleaningStore((s) => s.previewOriginal);
  const previewCleaned = useCleaningStore((s) => s.previewCleaned);

  if (!previewOriginal && !previewCleaned) return null;

  const delta = previewCleaned.length - previewOriginal.length;
  const deltaLabel = delta > 0 ? `+${delta}` : `${delta}`;

  return (
    <GlassPanel solid className="mt-3">
      <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
        Preview
      </h5>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <span className="text-xs text-text-muted block mb-1">Original</span>
          <div className="text-xs text-text-secondary bg-white/5 rounded-lg p-2 max-h-40 overflow-auto whitespace-pre-wrap">
            {previewOriginal}
          </div>
        </div>
        <div>
          <span className="text-xs text-text-muted block mb-1">Cleaned</span>
          <div className="text-xs text-text-secondary bg-white/5 rounded-lg p-2 max-h-40 overflow-auto whitespace-pre-wrap">
            {previewCleaned}
          </div>
        </div>
      </div>
      <p className="text-xs text-text-muted mt-2">
        {previewOriginal.length} → {previewCleaned.length} chars ({deltaLabel})
      </p>
    </GlassPanel>
  );
}
