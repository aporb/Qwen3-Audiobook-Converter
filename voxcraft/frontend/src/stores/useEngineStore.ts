import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiFetch } from "@/lib/api";
import type { Engine } from "@/lib/constants";

interface DeviceInfo {
  device: string;
  memory_available_gb: number;
  memory_total_gb: number;
  accelerator: string | null;
}

interface EngineStatus {
  mlx_loaded: boolean;
  mlx_model_id: string | null;
  openai_available: boolean;
}

interface ModelCacheStatus {
  cached: boolean;
  model_id: string;
  size_gb: number;
}

interface EngineState {
  engine: Engine;
  deviceInfo: DeviceInfo | null;
  status: EngineStatus | null;
  modelDownloading: boolean;
  modelDownloadProgress: number;
  modelDownloadMessage: string;
  modelCached: boolean | null;
  setEngine: (engine: Engine) => void;
  fetchDeviceInfo: () => Promise<void>;
  fetchStatus: () => Promise<void>;
  checkModelCached: (voiceMode: string) => Promise<boolean>;
  preloadModel: (voiceMode: string) => Promise<void>;
}

export const useEngineStore = create<EngineState>()(
  persist(
    (set, get) => ({
      engine: "mlx",
      deviceInfo: null,
      status: null,
      modelDownloading: false,
      modelDownloadProgress: 0,
      modelDownloadMessage: "",
      modelCached: null,

      setEngine: (engine) => set({ engine }),

      fetchDeviceInfo: async () => {
        const info = await apiFetch<DeviceInfo>("/system/device-info");
        set({ deviceInfo: info });
      },

      fetchStatus: async () => {
        const status = await apiFetch<EngineStatus>("/system/engine-status");
        set({ status });
      },

      checkModelCached: async (voiceMode: string) => {
        try {
          const res = await apiFetch<ModelCacheStatus>(
            `/system/model-cached/${voiceMode}`,
          );
          set({ modelCached: res.cached });
          return res.cached;
        } catch {
          set({ modelCached: null });
          return false;
        }
      },

      preloadModel: async (voiceMode: string) => {
        set({
          modelDownloading: true,
          modelDownloadProgress: 0,
          modelDownloadMessage: "Preparing download...",
        });

        try {
          // POST triggers the preload and returns an SSE stream
          const res = await fetch("/api/system/preload-model", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ voice_mode: voiceMode }),
          });

          if (!res.ok || !res.body) {
            set({ modelDownloading: false });
            return;
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              if (line.startsWith("event:")) {
                continue;
              }
              if (line.startsWith("data:")) {
                try {
                  const data = JSON.parse(line.slice(5).trim());
                  if (data.fraction !== undefined) {
                    set({
                      modelDownloadProgress: data.fraction,
                      modelDownloadMessage: data.message ?? "",
                    });
                  }
                  if (data.message === "Model ready") {
                    set({
                      modelDownloading: false,
                      modelDownloadProgress: 1,
                      modelDownloadMessage: "Model ready",
                      modelCached: true,
                    });
                    // Refresh engine status
                    get().fetchStatus().catch(() => {});
                    return;
                  }
                } catch {
                  // ignore parse errors
                }
              }
            }
          }

          set({ modelDownloading: false, modelCached: true });
          get().fetchStatus().catch(() => {});
        } catch {
          set({ modelDownloading: false });
        }
      },
    }),
    {
      name: "voxcraft-engine",
      partialize: (state) => ({ engine: state.engine }),
    },
  ),
);
