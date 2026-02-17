import { useEffect, type ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { DynamicIsland } from "./DynamicIsland";
import { ModelDownloadBanner } from "./ModelDownloadBanner";
import { useEngineStore } from "@/stores/useEngineStore";
import { detectDeploymentMode } from "@/lib/mode";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const fetchDeviceInfo = useEngineStore((s) => s.fetchDeviceInfo);
  const fetchStatus = useEngineStore((s) => s.fetchStatus);
  const engine = useEngineStore((s) => s.engine);
  const checkModelCached = useEngineStore((s) => s.checkModelCached);
  const preloadModel = useEngineStore((s) => s.preloadModel);
  const modelDownloading = useEngineStore((s) => s.modelDownloading);

  useEffect(() => {
    detectDeploymentMode().catch(() => {});
    fetchDeviceInfo().catch(() => {});
    fetchStatus().catch(() => {});

    // Poll status every 10s
    const interval = setInterval(() => {
      fetchStatus().catch(() => {});
    }, 10_000);
    return () => clearInterval(interval);
  }, [fetchDeviceInfo, fetchStatus]);

  // Auto-check and preload model for MLX engine
  useEffect(() => {
    if (engine !== "mlx") return;

    checkModelCached("custom_voice").then((cached) => {
      if (!cached && !modelDownloading) {
        preloadModel("custom_voice");
      }
    });
  }, [engine, checkModelCached, preloadModel, modelDownloading]);

  return (
    <div className="h-screen flex flex-col">
      <DynamicIsland />
      <Header />
      <ModelDownloadBanner />
      <div className="flex-1 flex overflow-hidden">
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
        <Sidebar />
      </div>
    </div>
  );
}
