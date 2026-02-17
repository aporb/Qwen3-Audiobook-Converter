import { create } from "zustand";

interface AudioState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  audioUrl: string | null;

  setPlaying: (playing: boolean) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setAudioUrl: (url: string | null) => void;
}

export const useAudioStore = create<AudioState>((set) => ({
  isPlaying: false,
  currentTime: 0,
  duration: 0,
  audioUrl: null,

  setPlaying: (playing) => set({ isPlaying: playing }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setAudioUrl: (url) => set({ audioUrl: url }),
}));
