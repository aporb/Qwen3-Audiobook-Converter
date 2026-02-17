import { create } from "zustand";
import { persist } from "zustand/middleware";
import { apiFetch, subscribeSSE } from "@/lib/api";
import type { CleaningBackend, CleaningPreset } from "@/lib/cleaning-presets";
import { PRESET_SYSTEM_PROMPTS } from "@/lib/cleaning-presets";

/** Function signature for browser-based LLM generation (from useWebLLM hook). */
export type BrowserGenerateFn = (systemPrompt: string, userContent: string, chunkIndex: number) => Promise<string>;

interface CleaningState {
  // Persisted config
  aiCleaningEnabled: boolean;
  cleaningBackend: CleaningBackend;
  cleaningPreset: CleaningPreset;
  customPrompt: string;
  customBaseUrl: string;
  customModel: string;
  customApiKey: string;
  browserModelId: string;

  // Runtime state (not persisted)
  isProcessing: boolean;
  progress: number;
  progressMessage: string;
  previewOriginal: string;
  previewCleaned: string;
  error: string | null;
  browserModelReady: boolean;
  browserModelDownloading: boolean;
  browserModelProgress: number;
  webgpuAvailable: boolean;

  // Actions
  setAiCleaningEnabled: (v: boolean) => void;
  setCleaningBackend: (v: CleaningBackend) => void;
  setCleaningPreset: (v: CleaningPreset) => void;
  setCustomPrompt: (v: string) => void;
  setCustomBaseUrl: (v: string) => void;
  setCustomModel: (v: string) => void;
  setCustomApiKey: (v: string) => void;
  setBrowserModelId: (v: string) => void;
  setBrowserModelReady: (v: boolean) => void;
  setBrowserModelDownloading: (v: boolean) => void;
  setBrowserModelProgress: (v: number) => void;
  setWebgpuAvailable: (v: boolean) => void;
  cleanTextViaBackend: (text: string) => Promise<string>;
  cleanTextViaBrowser: (text: string, generateFn: BrowserGenerateFn) => Promise<string>;
  cleanText: (text: string, browserGenerate?: BrowserGenerateFn) => Promise<string>;
  previewClean: (sampleText: string, browserGenerate?: BrowserGenerateFn) => Promise<void>;
  clearPreview: () => void;
  clearError: () => void;
}

export const useCleaningStore = create<CleaningState>()(
  persist(
    (set, get) => ({
      // Persisted config
      aiCleaningEnabled: false,
      cleaningBackend: "openai",
      cleaningPreset: "ocr_cleanup",
      customPrompt: "",
      customBaseUrl: "",
      customModel: "",
      customApiKey: "",
      browserModelId: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC",

      // Runtime state
      isProcessing: false,
      progress: 0,
      progressMessage: "",
      previewOriginal: "",
      previewCleaned: "",
      error: null,
      browserModelReady: false,
      browserModelDownloading: false,
      browserModelProgress: 0,
      webgpuAvailable: false,

      // Actions
      setAiCleaningEnabled: (v) => set({ aiCleaningEnabled: v }),
      setCleaningBackend: (v) => set({ cleaningBackend: v }),
      setCleaningPreset: (v) => set({ cleaningPreset: v }),
      setCustomPrompt: (v) => set({ customPrompt: v }),
      setCustomBaseUrl: (v) => set({ customBaseUrl: v }),
      setCustomModel: (v) => set({ customModel: v }),
      setCustomApiKey: (v) => set({ customApiKey: v }),
      setBrowserModelId: (v) => set({ browserModelId: v }),
      setBrowserModelReady: (v) => set({ browserModelReady: v }),
      setBrowserModelDownloading: (v) => set({ browserModelDownloading: v }),
      setBrowserModelProgress: (v) => set({ browserModelProgress: v }),
      setWebgpuAvailable: (v) => set({ webgpuAvailable: v }),

      cleanTextViaBackend: async (text) => {
        const state = get();
        set({ isProcessing: true, progress: 0, progressMessage: "Starting AI cleaning...", error: null });

        try {
          const body: Record<string, unknown> = {
            text,
            backend: state.cleaningBackend,
            preset: state.cleaningPreset,
            custom_prompt: state.cleaningPreset === "custom" ? state.customPrompt : undefined,
            custom_base_url: state.cleaningBackend === "custom" ? state.customBaseUrl : undefined,
            custom_model: state.cleaningBackend === "custom" ? state.customModel : undefined,
            custom_api_key: state.cleaningBackend === "custom" ? state.customApiKey : undefined,
          };

          const { task_id } = await apiFetch<{ task_id: string }>(
            "/cleaning/process",
            { method: "POST", body: JSON.stringify(body) },
          );

          return new Promise<string>((resolve, reject) => {
            subscribeSSE(
              `/cleaning/stream/${task_id}`,
              (evt) => {
                if (evt.event === "progress") {
                  set({
                    progress: (evt.data.fraction as number) ?? 0,
                    progressMessage: (evt.data.message as string) ?? "",
                  });
                } else if (evt.event === "complete") {
                  set({ isProcessing: false, progress: 1, progressMessage: "Cleaning complete!" });
                  resolve(evt.data.cleaned_text as string);
                } else if (evt.event === "error") {
                  const msg = (evt.data.message as string) ?? "Cleaning failed";
                  set({ isProcessing: false, error: msg });
                  reject(new Error(msg));
                }
              },
              () => {
                if (get().isProcessing) {
                  set({ isProcessing: false, error: "Connection lost" });
                  reject(new Error("Connection lost"));
                }
              },
            );
          });
        } catch (e) {
          set({ isProcessing: false, error: (e as Error).message });
          throw e;
        }
      },

      cleanTextViaBrowser: async (text, generateFn) => {
        const state = get();
        set({ isProcessing: true, progress: 0, progressMessage: "Starting browser AI cleaning...", error: null });

        try {
          const systemPrompt = state.cleaningPreset === "custom"
            ? state.customPrompt
            : (PRESET_SYSTEM_PROMPTS[state.cleaningPreset] ?? PRESET_SYSTEM_PROMPTS["ocr_cleanup"]!);

          const chunks = text.split(/\n\n+/).filter((c) => c.trim());
          if (chunks.length === 0) {
            set({ isProcessing: false, progress: 1, progressMessage: "Nothing to clean" });
            return text;
          }

          const cleanedParts: string[] = [];
          for (let i = 0; i < chunks.length; i++) {
            set({
              progress: (i + 1) / chunks.length,
              progressMessage: `Cleaning chunk ${i + 1}/${chunks.length}`,
            });
            const cleaned = await generateFn(systemPrompt, chunks[i]!, i);
            cleanedParts.push(cleaned);
          }

          const result = cleanedParts.join("\n\n");
          set({ isProcessing: false, progress: 1, progressMessage: "Cleaning complete!" });
          return result;
        } catch (e) {
          set({ isProcessing: false, error: (e as Error).message });
          throw e;
        }
      },

      cleanText: async (text, browserGenerate) => {
        const state = get();
        if (state.cleaningBackend === "browser") {
          if (!browserGenerate) throw new Error("Browser generate function required for browser cleaning");
          if (!state.browserModelReady) {
            const msg = "Browser model not loaded. Click 'Download & Load Model' in the AI Text Cleaning panel first.";
            set({ error: msg });
            throw new Error(msg);
          }
          return get().cleanTextViaBrowser(text, browserGenerate);
        }
        return get().cleanTextViaBackend(text);
      },

      previewClean: async (sampleText, browserGenerate?) => {
        const state = get();
        set({ error: null });

        const sample = sampleText.slice(0, 500);

        // Browser preview: clean locally via WebLLM
        if (state.cleaningBackend === "browser") {
          if (!browserGenerate) {
            set({ error: "Browser model not available for preview" });
            return;
          }
          try {
            const systemPrompt = state.cleaningPreset === "custom"
              ? state.customPrompt
              : (PRESET_SYSTEM_PROMPTS[state.cleaningPreset] ?? PRESET_SYSTEM_PROMPTS["ocr_cleanup"]!);
            const cleaned = await browserGenerate(systemPrompt, sample, 0);
            set({ previewOriginal: sample, previewCleaned: cleaned });
          } catch (e) {
            set({ error: (e as Error).message });
          }
          return;
        }

        // Server preview: call backend API
        try {
          const body: Record<string, unknown> = {
            text: sample,
            backend: state.cleaningBackend,
            preset: state.cleaningPreset,
            custom_prompt: state.cleaningPreset === "custom" ? state.customPrompt : undefined,
            custom_base_url: state.cleaningBackend === "custom" ? state.customBaseUrl : undefined,
            custom_model: state.cleaningBackend === "custom" ? state.customModel : undefined,
            custom_api_key: state.cleaningBackend === "custom" ? state.customApiKey : undefined,
          };

          const res = await apiFetch<{ original: string; cleaned: string }>(
            "/cleaning/preview",
            { method: "POST", body: JSON.stringify(body) },
          );

          set({ previewOriginal: res.original, previewCleaned: res.cleaned });
        } catch (e) {
          set({ error: (e as Error).message });
        }
      },

      clearPreview: () => set({ previewOriginal: "", previewCleaned: "" }),
      clearError: () => set({ error: null }),
    }),
    {
      name: "voxcraft-cleaning",
      partialize: (state) => ({
        aiCleaningEnabled: state.aiCleaningEnabled,
        cleaningBackend: state.cleaningBackend,
        cleaningPreset: state.cleaningPreset,
        customPrompt: state.customPrompt,
        customBaseUrl: state.customBaseUrl,
        customModel: state.customModel,
        customApiKey: state.customApiKey,
        browserModelId: state.browserModelId,
      }),
    },
  ),
);
