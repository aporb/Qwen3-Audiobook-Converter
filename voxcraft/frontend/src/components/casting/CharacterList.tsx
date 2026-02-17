import { useCastingStore } from "@/stores/useCastingStore";
import { CharacterCard } from "./CharacterCard";

export function CharacterList() {
  const characters = useCastingStore((s) => s.characters);

  if (characters.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
        Characters ({characters.length})
      </h3>
      {characters.map((ch) => (
        <CharacterCard
          key={ch.name}
          name={ch.name}
          description={ch.description}
          lineCount={ch.line_count}
          sampleLines={ch.sample_lines}
        />
      ))}
    </div>
  );
}
