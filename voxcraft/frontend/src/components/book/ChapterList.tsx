import { clsx } from "clsx";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { useProjectStore } from "@/stores/useProjectStore";

export function ChapterList() {
  const metadata = useProjectStore((s) => s.metadata);
  const selectedChapters = useProjectStore((s) => s.selectedChapters);
  const toggleChapter = useProjectStore((s) => s.toggleChapter);
  const selectAllChapters = useProjectStore((s) => s.selectAllChapters);
  const setSelectedChapters = useProjectStore((s) => s.setSelectedChapters);

  if (!metadata || metadata.chapters.length === 0) return null;

  const allSelected = selectedChapters.length === metadata.chapters.length;
  const selectedWords = metadata.chapters
    .filter((ch) => selectedChapters.includes(ch.id))
    .reduce((sum, ch) => sum + ch.word_count, 0);

  return (
    <GlassPanel solid className="animate-slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Chapters ({selectedChapters.length}/{metadata.chapters.length})
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            allSelected ? setSelectedChapters([]) : selectAllChapters()
          }
        >
          {allSelected ? "Deselect All" : "Select All"}
        </Button>
      </div>

      <div className="max-h-64 overflow-y-auto flex flex-col gap-1">
        {metadata.chapters.map((ch) => {
          const selected = selectedChapters.includes(ch.id);
          return (
            <button
              key={ch.id}
              onClick={() => toggleChapter(ch.id)}
              className={clsx(
                "flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors",
                selected
                  ? "bg-white/10 border border-white/15"
                  : "hover:bg-white/5 border border-transparent",
              )}
            >
              <div className="flex items-center gap-2 min-w-0">
                <div
                  className={clsx(
                    "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0",
                    selected
                      ? "bg-white border-white"
                      : "border-glass-border",
                  )}
                >
                  {selected && (
                    <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                      <path
                        d="M2 6L5 9L10 3"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </div>
                <span className="text-sm text-text-primary truncate">
                  {ch.title}
                </span>
              </div>
              <span className="text-xs text-text-muted flex-shrink-0 ml-2">
                {ch.word_count.toLocaleString()}w
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-glass-border text-xs text-text-secondary">
        Selected: {selectedWords.toLocaleString()} words
      </div>
    </GlassPanel>
  );
}
