import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PreferencesState {
  // Voice
  voiceMode: string;
  speaker: string;
  language: string;
  openaiVoice: string;
  openaiModel: string;

  // Voice Design / Clone
  voiceDescription: string;
  selectedVoiceId: string | null;
  refText: string;
  refAudioPath: string | null; // not persisted — populated from voice library

  // Text processing
  fixCapitals: boolean;
  removeFootnotes: boolean;
  normalizeChars: boolean;

  // Actions
  setVoiceMode: (v: string) => void;
  setSpeaker: (v: string) => void;
  setLanguage: (v: string) => void;
  setOpenaiVoice: (v: string) => void;
  setOpenaiModel: (v: string) => void;
  setVoiceDescription: (v: string) => void;
  setSelectedVoiceId: (v: string | null) => void;
  setRefAudioPath: (v: string | null) => void;
  setRefText: (v: string) => void;
  setFixCapitals: (v: boolean) => void;
  setRemoveFootnotes: (v: boolean) => void;
  setNormalizeChars: (v: boolean) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      voiceMode: "custom_voice",
      speaker: "Ryan",
      language: "english",
      openaiVoice: "coral",
      openaiModel: "gpt-4o-mini-tts",
      voiceDescription: "",
      selectedVoiceId: null,
      refText: "",
      refAudioPath: null,
      fixCapitals: true,
      removeFootnotes: true,
      normalizeChars: true,

      setVoiceMode: (v) => set({ voiceMode: v }),
      setSpeaker: (v) => set({ speaker: v }),
      setLanguage: (v) => set({ language: v }),
      setOpenaiVoice: (v) => set({ openaiVoice: v }),
      setOpenaiModel: (v) => set({ openaiModel: v }),
      setVoiceDescription: (v) => set({ voiceDescription: v }),
      setSelectedVoiceId: (v) => set({ selectedVoiceId: v }),
      setRefAudioPath: (v) => set({ refAudioPath: v }),
      setRefText: (v) => set({ refText: v }),
      setFixCapitals: (v) => set({ fixCapitals: v }),
      setRemoveFootnotes: (v) => set({ removeFootnotes: v }),
      setNormalizeChars: (v) => set({ normalizeChars: v }),
    }),
    {
      name: "voxcraft-preferences",
      partialize: (state) => ({
        voiceMode: state.voiceMode,
        speaker: state.speaker,
        language: state.language,
        openaiVoice: state.openaiVoice,
        openaiModel: state.openaiModel,
        voiceDescription: state.voiceDescription,
        selectedVoiceId: state.selectedVoiceId,
        refText: state.refText,
        // refAudioPath intentionally excluded — rebuilt from voiceId on use
        fixCapitals: state.fixCapitals,
        removeFootnotes: state.removeFootnotes,
        normalizeChars: state.normalizeChars,
      }),
    },
  ),
);
