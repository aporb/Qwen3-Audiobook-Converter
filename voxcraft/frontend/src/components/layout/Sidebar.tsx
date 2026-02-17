import { clsx } from "clsx";
import { useUIStore } from "@/stores/useUIStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { useAppStore } from "@/stores/useAppStore";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Badge } from "@/components/shared/Badge";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { SettingsPanel } from "@/components/settings/SettingsPanel";

export function Sidebar() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const sidebarContext = useUIStore((s) => s.sidebarContext);
  const engine = useEngineStore((s) => s.engine);
  const setEngine = useEngineStore((s) => s.setEngine);
  const deviceInfo = useEngineStore((s) => s.deviceInfo);
  const status = useEngineStore((s) => s.status);
  const deploymentMode = useAppStore((s) => s.deploymentMode);

  if (!sidebarOpen) return null;

  // Settings context — show settings panel
  if (sidebarContext === "settings") {
    return (
      <aside className="w-72 border-l border-glass-border bg-obsidian/60 backdrop-blur-lg p-4 overflow-y-auto">
        <h2 className="text-sm font-semibold text-text-primary mb-4">Settings</h2>
        <SettingsPanel />
      </aside>
    );
  }

  // Default: engine/status view
  return (
    <aside className="w-72 border-l border-glass-border bg-obsidian/60 backdrop-blur-lg p-4 flex flex-col gap-4 overflow-y-auto">
      {/* Engine Toggle — hide in cloud mode (no MLX available) */}
      {deploymentMode !== "cloud" && (
        <GlassPanel solid>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Engine
          </h3>
          <div className="flex gap-2" data-tour="engine-toggle">
            <button
              onClick={() => setEngine("mlx")}
              className={clsx(
                "flex-1 py-2 text-xs font-medium rounded-lg transition-all",
                engine === "mlx"
                  ? "bg-white/10 text-white border border-white/15"
                  : "text-text-muted hover:text-text-secondary border border-transparent",
              )}
            >
              Privacy Mode
            </button>
            <button
              onClick={() => setEngine("openai")}
              className={clsx(
                "flex-1 py-2 text-xs font-medium rounded-lg transition-all",
                engine === "openai"
                  ? "bg-white/10 text-white border border-white/15"
                  : "text-text-muted hover:text-text-secondary border border-transparent",
              )}
            >
              Studio Mode
            </button>
          </div>
        </GlassPanel>
      )}

      {/* Engine Status */}
      {status && (
        <GlassPanel solid>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Status
          </h3>
          <div className="flex flex-col gap-2">
            {deploymentMode !== "cloud" && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary">MLX Engine</span>
                <Badge variant={status.mlx_loaded ? "active" : "inactive"} dot>
                  {status.mlx_loaded ? "Loaded" : "Idle"}
                </Badge>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">OpenAI API</span>
              <Badge
                variant={status.openai_available ? "active" : "inactive"}
                dot
              >
                {status.openai_available ? "Available" : "No Key"}
              </Badge>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* Device Info */}
      {deviceInfo && (
        <GlassPanel solid>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Device
          </h3>
          <p className="text-xs text-text-secondary mb-2">{deviceInfo.device}</p>
          {deviceInfo.memory_total_gb > 0 && (
            <ProgressBar
              value={
                (deviceInfo.memory_total_gb - deviceInfo.memory_available_gb) /
                deviceInfo.memory_total_gb
              }
              label={`Memory: ${deviceInfo.memory_available_gb}GB / ${deviceInfo.memory_total_gb}GB`}
              variant="local"
            />
          )}
        </GlassPanel>
      )}
    </aside>
  );
}
