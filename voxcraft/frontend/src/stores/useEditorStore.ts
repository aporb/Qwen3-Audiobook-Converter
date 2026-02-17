import { create } from "zustand";

interface EditorState {
  content: string;
  selection: string;
  paragraphSpeakers: Record<string, string>;

  setContent: (content: string) => void;
  setSelection: (selection: string) => void;
  setSpeaker: (paragraphId: string, speaker: string) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  content: "",
  selection: "",
  paragraphSpeakers: {},

  setContent: (content) => set({ content }),
  setSelection: (selection) => set({ selection }),
  setSpeaker: (paragraphId, speaker) =>
    set((s) => ({
      paragraphSpeakers: { ...s.paragraphSpeakers, [paragraphId]: speaker },
    })),
}));
