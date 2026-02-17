import { useEffect, useState } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { useEngineStore } from "@/stores/useEngineStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { apiFetch } from "@/lib/api";

interface CostData {
  characters: number;
  model: string;
  estimated_cost_usd: number;
  estimated_duration_min: number;
}

export function CostEstimate() {
  const engine = useEngineStore((s) => s.engine);
  const metadata = useProjectStore((s) => s.metadata);
  const selectedChapters = useProjectStore((s) => s.selectedChapters);
  const [cost, setCost] = useState<CostData | null>(null);

  const selectedWords = metadata?.chapters
    .filter((ch) => selectedChapters.includes(ch.id))
    .reduce((sum, ch) => sum + ch.word_count, 0) ?? 0;

  // Rough character estimate (avg 5 chars/word)
  const estimatedChars = selectedWords * 5;

  useEffect(() => {
    if (engine !== "openai" || estimatedChars === 0) {
      setCost(null);
      return;
    }
    apiFetch<CostData>("/tts/estimate-cost", {
      method: "POST",
      body: JSON.stringify({ text: "x".repeat(Math.min(estimatedChars, 100)), model: "gpt-4o-mini-tts" }),
    }).then((data) => {
      // Scale up from actual chars
      const scale = estimatedChars / data.characters;
      setCost({
        ...data,
        characters: estimatedChars,
        estimated_cost_usd: Math.round(data.estimated_cost_usd * scale * 10000) / 10000,
        estimated_duration_min: Math.round(data.estimated_duration_min * scale * 10) / 10,
      });
    }).catch(() => setCost(null));
  }, [engine, estimatedChars]);

  if (!metadata) return null;

  return (
    <GlassPanel solid className="animate-slide-up">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Estimate
      </h3>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-text-muted">Words</p>
          <p className="text-sm font-medium text-text-primary">
            {selectedWords.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-xs text-text-muted">Est. Duration</p>
          <p className="text-sm font-medium text-text-primary">
            ~{Math.round(selectedWords / 150)} min
          </p>
        </div>
        {engine === "mlx" && (
          <div className="col-span-2">
            <p className="text-xs text-white/70 font-medium">
              Free — runs locally on your device
            </p>
          </div>
        )}
        {engine === "openai" && cost && (
          <>
            <div>
              <p className="text-xs text-text-muted">API Cost</p>
              <p className="text-sm font-medium text-white/70">
                ~${cost.estimated_cost_usd.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Characters</p>
              <p className="text-sm font-medium text-text-primary">
                {cost.characters.toLocaleString()}
              </p>
            </div>
          </>
        )}
      </div>
    </GlassPanel>
  );
}
