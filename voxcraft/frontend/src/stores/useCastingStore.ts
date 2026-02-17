import { create } from "zustand";

interface Character {
  name: string;
  description: string;
  line_count: number;
  sample_lines: string[];
}

interface VoiceAssignment {
  character_name: string;
  voice: string;
  engine: string;
}

interface CastingState {
  characters: Character[];
  assignments: VoiceAssignment[];
  isAnalyzing: boolean;
  error: string | null;

  setCharacters: (chars: Character[]) => void;
  setAssignment: (name: string, voice: string, engine: string) => void;
  setAnalyzing: (v: boolean) => void;
  setError: (e: string | null) => void;
}

export const useCastingStore = create<CastingState>((set) => ({
  characters: [],
  assignments: [],
  isAnalyzing: false,
  error: null,

  setCharacters: (chars) => set({ characters: chars }),
  setAssignment: (name, voice, engine) =>
    set((s) => ({
      assignments: [
        ...s.assignments.filter((a) => a.character_name !== name),
        { character_name: name, voice, engine },
      ],
    })),
  setAnalyzing: (v) => set({ isAnalyzing: v }),
  setError: (e) => set({ error: e }),
}));
