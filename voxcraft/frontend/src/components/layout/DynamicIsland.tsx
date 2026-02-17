import { clsx } from "clsx";
import { useUIStore } from "@/stores/useUIStore";
import { ProgressBar } from "@/components/shared/ProgressBar";

export function DynamicIsland() {
  const { visible, label, progress } = useUIStore((s) => s.island);

  if (!visible) return null;

  return (
    <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50">
      <div
        className={clsx(
          "glass-panel-solid px-5 py-2.5 flex items-center gap-3 min-w-[240px] shadow-2xl shadow-black/40",
          visible ? "animate-island-in" : "animate-island-out",
        )}
      >
        <div className="w-2 h-2 rounded-full bg-white animate-pulse-dot" />
        <div className="flex-1">
          <p className="text-xs text-text-secondary">{label}</p>
          {progress > 0 && progress < 1 && (
            <ProgressBar value={progress} className="mt-1" />
          )}
        </div>
      </div>
    </div>
  );
}
