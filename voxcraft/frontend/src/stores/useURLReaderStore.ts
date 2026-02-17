import { create } from "zustand";
import { apiFetch, subscribeSSE } from "@/lib/api";

export type ProcessingMode = "full_article" | "summary_insights";

export interface URLContent {
  title: string;
  content: string;
  author?: string;
  published_date?: string;
  word_count: number;
  estimated_duration_min: number;
  url: string;
}

interface ConvertOptions {
  engine: "mlx" | "openai";
  voice_mode?: "custom_voice" | "voice_clone" | "voice_design";
  voice: string;
  language?: string;
  instruct?: string;
  ref_audio?: string;
  ref_text?: string;
  voice_description?: string;
  openai_model?: string;
  openai_voice?: string;
  instructions?: string;
  openai_api_key?: string;
  content_override?: string;
}

export interface URLReaderState {
  url: string;
  content: URLContent | null;
  mode: ProcessingMode;

  isFetching: boolean;
  isConverting: boolean;

  taskId: string | null;
  progress: number; // 0..1
  progressMessage: string;
  audioUrl: string | null;
  audioDuration: number | null;

  error: string | null;

  setUrl: (url: string) => void;
  setMode: (mode: ProcessingMode) => void;
  fetchContent: (url: string) => Promise<void>;
  convertContent: (options: ConvertOptions) => Promise<void>;
  reset: () => void;
  resetContent: () => void;
}

export const useURLReaderStore = create<URLReaderState>((set, get) => ({
  url: "",
  content: null,
  mode: "full_article",
  isFetching: false,
  isConverting: false,
  taskId: null,
  progress: 0,
  progressMessage: "",
  audioUrl: null,
  audioDuration: null,
  error: null,

  setUrl: (url) => set({ url }),
  setMode: (mode) => set({ mode }),

  fetchContent: async (url) => {
    set({
      isFetching: true,
      error: null,
      content: null,
      audioUrl: null,
      audioDuration: null,
      progress: 0,
      progressMessage: "",
    });

    try {
      const content = await apiFetch<URLContent>("/url-reader/fetch", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      set({ content, isFetching: false, url });
    } catch (e) {
      set({
        isFetching: false,
        error: (e as Error).message || "Failed to fetch URL",
      });
    }
  },

  convertContent: async (options) => {
    const { content, url, mode } = get();

    if (!content && !url) {
      set({ error: "No URL/content available to convert" });
      return;
    }

    set({
      isConverting: true,
      progress: 0,
      progressMessage: "Starting conversion...",
      audioUrl: null,
      audioDuration: null,
      error: null,
    });

    try {
      const { task_id } = await apiFetch<{ task_id: string }>("/url-reader/convert", {
        method: "POST",
        body: JSON.stringify({
          url: url || content?.url,
          mode,
          content: options.content_override ?? content?.content,
          engine: options.engine,
          voice_mode: options.voice_mode ?? "custom_voice",
          voice: options.voice,
          language: options.language ?? "english",
          instruct: options.instruct,
          ref_audio: options.ref_audio,
          ref_text: options.ref_text,
          voice_description: options.voice_description,
          openai_model: options.openai_model,
          openai_voice: options.openai_voice,
          instructions: options.instructions,
          openai_api_key: options.openai_api_key,
        }),
      });

      set({ taskId: task_id });

      subscribeSSE(
        `/url-reader/stream/${task_id}`,
        (evt) => {
          if (evt.event === "progress") {
            const fraction =
              typeof evt.data.fraction === "number"
                ? (evt.data.fraction as number)
                : typeof evt.data.progress === "number"
                  ? (evt.data.progress as number)
                  : 0;

            set({
              progress: Math.min(Math.max(fraction, 0), 1),
              progressMessage: (evt.data.message as string) ?? "",
            });
          } else if (evt.event === "complete") {
            set({
              isConverting: false,
              progress: 1,
              progressMessage: "Done!",
              audioUrl: evt.data.audio_url as string,
              audioDuration: evt.data.duration as number,
            });
          } else if (evt.event === "error") {
            set({
              isConverting: false,
              error: (evt.data.message as string) ?? "Conversion failed",
            });
          }
        },
        () => {
          if (get().isConverting) {
            set({ isConverting: false, error: "Connection lost" });
          }
        },
      );
    } catch (e) {
      set({
        isConverting: false,
        error: (e as Error).message || "Conversion failed",
      });
    }
  },

  reset: () =>
    set({
      url: "",
      content: null,
      mode: "full_article",
      isFetching: false,
      isConverting: false,
      taskId: null,
      progress: 0,
      progressMessage: "",
      audioUrl: null,
      audioDuration: null,
      error: null,
    }),

  resetContent: () =>
    set({
      content: null,
      audioUrl: null,
      audioDuration: null,
      progress: 0,
      progressMessage: "",
      error: null,
    }),
}));
