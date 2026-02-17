import { clsx } from "clsx";

interface ProgressBarProps {
  value: number; // 0–1
  label?: string;
  className?: string;
  variant?: "default" | "local" | "cloud";
}

const gradients: Record<string, string> = {
  default: "from-white/60 to-white/30",
  local: "from-white/70 to-white/40",
  cloud: "from-zinc-400 to-zinc-500",
};

export function ProgressBar({
  value,
  label,
  className,
  variant = "default",
}: ProgressBarProps) {
  const pct = Math.min(Math.max(value, 0), 1) * 100;

  return (
    <div className={clsx("w-full", className)}>
      {label && (
        <div className="flex justify-between text-xs text-text-secondary mb-1">
          <span>{label}</span>
          <span>{Math.round(pct)}%</span>
        </div>
      )}
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full bg-gradient-to-r transition-all duration-300",
            gradients[variant],
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
