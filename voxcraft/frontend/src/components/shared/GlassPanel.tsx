import { clsx } from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
  solid?: boolean;
  padding?: boolean;
}

export function GlassPanel({
  children,
  className,
  solid = false,
  padding = true,
  ...props
}: GlassPanelProps) {
  return (
    <div
      className={clsx(
        solid ? "glass-panel-solid" : "glass-panel",
        padding && "p-4",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
