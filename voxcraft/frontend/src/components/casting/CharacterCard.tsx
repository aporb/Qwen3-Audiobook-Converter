import { GlassPanel } from "@/components/shared/GlassPanel";
import { Badge } from "@/components/shared/Badge";
import { Dropdown } from "@/components/shared/Dropdown";
import { useEngineStore } from "@/stores/useEngineStore";
import { useCastingStore } from "@/stores/useCastingStore";
import { MLX_SPEAKERS, OPENAI_VOICES } from "@/lib/constants";

interface CharacterCardProps {
  name: string;
  description: string;
  lineCount: number;
  sampleLines: string[];
}

export function CharacterCard({
  name,
  description,
  lineCount,
  sampleLines,
}: CharacterCardProps) {
  const engine = useEngineStore((s) => s.engine);
  const assignments = useCastingStore((s) => s.assignments);
  const setAssignment = useCastingStore((s) => s.setAssignment);

  const currentAssignment = assignments.find((a) => a.character_name === name);
  const currentVoice = currentAssignment?.voice ?? "";

  const voiceOptions =
    engine === "mlx"
      ? MLX_SPEAKERS.map((s) => ({ value: s, label: s }))
      : OPENAI_VOICES.map((v) => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1) }));

  return (
    <GlassPanel solid className="animate-slide-up">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="text-sm font-semibold text-text-primary">{name}</h4>
          <p className="text-xs text-text-secondary mt-0.5">{description}</p>
        </div>
        <Badge variant="info">{lineCount} lines</Badge>
      </div>

      {/* Sample dialogue */}
      {sampleLines.length > 0 && (
        <div className="mb-3 space-y-1">
          {sampleLines.slice(0, 2).map((line, i) => (
            <p
              key={i}
              className="text-xs text-text-muted italic pl-3 border-l-2 border-white/20"
            >
              &ldquo;{line}&rdquo;
            </p>
          ))}
        </div>
      )}

      {/* Voice Assignment */}
      <Dropdown
        label="Assign Voice"
        options={[{ value: "", label: "— Select —" }, ...voiceOptions]}
        value={currentVoice}
        onChange={(v) => setAssignment(name, v, engine)}
      />
    </GlassPanel>
  );
}
