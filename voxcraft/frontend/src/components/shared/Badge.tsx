import { clsx } from "clsx";
import type { ReactNode } from "react";

type BadgeVariant = "active" | "info" | "inactive" | "local" | "cloud";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
  dot?: boolean;
}

const styles: Record<BadgeVariant, string> = {
  active: "bg-white/10 text-white border-white/20",
  info: "bg-white/5 text-text-secondary border-white/10",
  inactive: "bg-white/5 text-text-muted border-white/5",
  local: "bg-white/10 text-white border-white/15",
  cloud: "bg-white/[0.08] text-zinc-300 border-white/10",
};

export function Badge({
  variant = "info",
  children,
  className,
  dot = false,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full border",
        styles[variant],
        className,
      )}
    >
      {dot && (
        <span
          className={clsx(
            "w-1.5 h-1.5 rounded-full",
            variant === "active" && "bg-white animate-pulse-dot",
            variant === "local" && "bg-white animate-pulse-dot",
            variant === "cloud" && "bg-zinc-400 animate-pulse-dot",
            variant === "info" && "bg-zinc-400",
            variant === "inactive" && "bg-text-muted",
          )}
        />
      )}
      {children}
    </span>
  );
}
