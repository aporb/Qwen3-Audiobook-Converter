import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { useCastingStore } from "@/stores/useCastingStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { CharacterList } from "./CharacterList";
import { apiFetch } from "@/lib/api";

export function CastingDirector() {
  const bookId = useProjectStore((s) => s.bookId);
  const metadata = useProjectStore((s) => s.metadata);
  const isAnalyzing = useCastingStore((s) => s.isAnalyzing);
  const setAnalyzing = useCastingStore((s) => s.setAnalyzing);
  const setCharacters = useCastingStore((s) => s.setCharacters);
  const setError = useCastingStore((s) => s.setError);
  const error = useCastingStore((s) => s.error);
  const characters = useCastingStore((s) => s.characters);

  const handleAnalyze = async () => {
    if (!bookId) return;
    setAnalyzing(true);
    setError(null);
    try {
      const data = await apiFetch<{ characters: typeof characters }>(
        "/casting/analyze",
        { method: "POST", body: JSON.stringify({ book_id: bookId }) },
      );
      setCharacters(data.characters);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (!bookId || !metadata) {
    return (
      <GlassPanel solid className="text-center py-8">
        <p className="text-sm text-text-secondary">
          Upload a book first to analyze characters.
        </p>
      </GlassPanel>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">
            Casting Director
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            AI-powered character detection for {metadata.title}
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          loading={isAnalyzing}
          onClick={handleAnalyze}
        >
          {characters.length > 0 ? "Re-analyze" : "Analyze Characters"}
        </Button>
      </div>

      {error && (
        <GlassPanel solid className="border-red-500/30">
          <p className="text-sm text-red-400">{error}</p>
        </GlassPanel>
      )}

      <CharacterList />
    </div>
  );
}
