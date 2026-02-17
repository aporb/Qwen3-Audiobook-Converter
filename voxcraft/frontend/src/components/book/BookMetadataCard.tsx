import { GlassPanel } from "@/components/shared/GlassPanel";
import { Badge } from "@/components/shared/Badge";
import { useProjectStore } from "@/stores/useProjectStore";

export function BookMetadataCard() {
  const metadata = useProjectStore((s) => s.metadata);

  if (!metadata) return null;

  return (
    <GlassPanel solid className="flex gap-4 animate-slide-up">
      {/* Cover */}
      {metadata.cover_image && (
        <img
          src={metadata.cover_image}
          alt="Cover"
          className="w-20 h-28 rounded-lg object-cover flex-shrink-0"
        />
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-text-primary truncate">
          {metadata.title}
        </h3>
        <p className="text-sm text-text-secondary mt-0.5">{metadata.author}</p>
        <div className="flex flex-wrap gap-2 mt-2">
          <Badge variant="info">{metadata.format.toUpperCase()}</Badge>
          <Badge variant="inactive">
            {metadata.total_words.toLocaleString()} words
          </Badge>
          <Badge variant="inactive">
            {metadata.chapters.length} chapters
          </Badge>
        </div>
      </div>
    </GlassPanel>
  );
}
