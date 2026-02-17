import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/stores/useAppStore";

export interface VoiceProfile {
  id: string;
  name: string;
  audio_filename: string;
  ref_text: string;
  created_at: string;
}

interface VoiceState {
  voices: VoiceProfile[];
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;

  fetchVoices: () => Promise<void>;
  uploadVoice: (file: File | Blob, name: string, refText: string) => Promise<VoiceProfile>;
  deleteVoice: (id: string) => Promise<void>;
}

export const useVoiceStore = create<VoiceState>()((set, get) => ({
  voices: [],
  isLoading: false,
  isUploading: false,
  error: null,

  fetchVoices: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiFetch<{ voices: VoiceProfile[] }>("/voices");
      set({ voices: res.voices, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  uploadVoice: async (file: File | Blob, name: string, refText: string) => {
    set({ isUploading: true, error: null });
    try {
      const form = new FormData();
      // Handle both File and Blob (from MediaRecorder)
      if (file instanceof File) {
        form.append("file", file);
      } else {
        form.append("file", file, "recording.webm");
      }
      form.append("name", name);
      form.append("ref_text", refText);

      const { openaiApiKey, sessionId } = useAppStore.getState();
      const headers: Record<string, string> = {};
      if (openaiApiKey) headers["X-OpenAI-Key"] = openaiApiKey;
      if (sessionId) headers["X-Session-Id"] = sessionId;

      const res = await fetch("/api/voices/upload", {
        method: "POST",
        body: form,
        headers,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || res.statusText);
      }

      const data = await res.json();

      // Refresh the voice list
      await get().fetchVoices();

      set({ isUploading: false });
      // Return the profile from the refreshed list
      const profile = get().voices.find((v) => v.id === data.id);
      return profile ?? { id: data.id, name, audio_filename: data.audio_filename, ref_text: refText, created_at: new Date().toISOString() };
    } catch (e) {
      set({ error: (e as Error).message, isUploading: false });
      throw e;
    }
  },

  deleteVoice: async (id: string) => {
    try {
      await apiFetch(`/voices/${id}`, { method: "DELETE" });
      set({ voices: get().voices.filter((v) => v.id !== id) });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },
}));
