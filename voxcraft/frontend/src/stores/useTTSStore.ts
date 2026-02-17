import { create } from "zustand";
import { apiFetch, subscribeSSE } from "@/lib/api";

interface TTSState {
  taskId: string | null;
  progress: number;
  progressMessage: string;
  audioUrl: string | null;
  audioDuration: number | null;
  sourceText: string | null;
  isGenerating: boolean;
  error: string | null;

  generateSpeech: (body: Record<string, unknown>) => Promise<void>;
  reset: () => void;
}

export const useTTSStore = create<TTSState>((set, get) => ({
  taskId: null,
  progress: 0,
  progressMessage: "",
  audioUrl: null,
  audioDuration: null,
  sourceText: null,
  isGenerating: false,
  error: null,

  generateSpeech: async (body) => {
    set({
      isGenerating: true,
      progress: 0,
      progressMessage: "Starting...",
      audioUrl: null,
      audioDuration: null,
      sourceText: typeof body.text === "string" ? body.text : null,
      error: null,
    });

    try {
      const { task_id } = await apiFetch<{ task_id: string }>(
        "/tts/generate",
        { method: "POST", body: JSON.stringify(body) },
      );
      set({ taskId: task_id });

      subscribeSSE(
        `/tts/stream/${task_id}`,
        (evt) => {
          if (evt.event === "progress") {
            set({
              progress: (evt.data.fraction as number) ?? 0,
              progressMessage: (evt.data.message as string) ?? "",
            });
          } else if (evt.event === "complete") {
            set({
              isGenerating: false,
              progress: 1,
              progressMessage: "Done!",
              audioUrl: evt.data.audio_url as string,
              audioDuration: evt.data.duration as number,
            });
          } else if (evt.event === "error") {
            set({
              isGenerating: false,
              error: (evt.data.message as string) ?? "Generation failed",
            });
          }
        },
        () => {
          if (get().isGenerating) {
            set({ isGenerating: false, error: "Connection lost" });
          }
        },
      );
    } catch (e) {
      set({ isGenerating: false, error: (e as Error).message });
    }
  },

  reset: () =>
    set({
      taskId: null,
      progress: 0,
      progressMessage: "",
      audioUrl: null,
      audioDuration: null,
      sourceText: null,
      isGenerating: false,
      error: null,
    }),
}));
