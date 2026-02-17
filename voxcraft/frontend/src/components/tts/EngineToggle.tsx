import { clsx } from "clsx";
import { useEngineStore } from "@/stores/useEngineStore";
import type { Engine } from "@/lib/constants";

export function EngineToggle() {
  const engine = useEngineStore((s) => s.engine);
  const setEngine = useEngineStore((s) => s.setEngine);

  const options: { value: Engine; label: string }[] = [
    { value: "mlx", label: "Local (MLX)" },
    { value: "openai", label: "Cloud (OpenAI)" },
  ];

  return (
    <div className="flex items-center gap-2 p-1 bg-white/5 rounded-lg">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setEngine(opt.value)}
          className={clsx(
            "flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-all",
            engine === opt.value
              ? "bg-white/10 text-white border border-white/15"
              : "text-text-muted hover:text-text-secondary",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
