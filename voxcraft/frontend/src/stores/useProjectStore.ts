import { create } from "zustand";
import { apiUpload } from "@/lib/api";

interface ChapterInfo {
  id: string;
  title: string;
  word_count: number;
}

interface BookMetadata {
  book_id: string;
  title: string;
  author: string;
  format: string;
  total_words: number;
  has_cover: boolean;
  chapters: ChapterInfo[];
  cover_image?: string | null;
}

interface ProjectState {
  bookId: string | null;
  metadata: BookMetadata | null;
  selectedChapters: string[];
  isUploading: boolean;
  error: string | null;

  uploadBook: (file: File) => Promise<void>;
  setSelectedChapters: (ids: string[]) => void;
  toggleChapter: (id: string) => void;
  selectAllChapters: () => void;
  clearBook: () => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  bookId: null,
  metadata: null,
  selectedChapters: [],
  isUploading: false,
  error: null,

  uploadBook: async (file) => {
    set({ isUploading: true, error: null });
    try {
      const data = await apiUpload<BookMetadata>("/books/upload", file);
      set({
        bookId: data.book_id,
        metadata: data,
        selectedChapters: data.chapters.map((ch) => ch.id),
        isUploading: false,
      });
    } catch (e) {
      set({ isUploading: false, error: (e as Error).message });
    }
  },

  setSelectedChapters: (ids) => set({ selectedChapters: ids }),

  toggleChapter: (id) =>
    set((s) => ({
      selectedChapters: s.selectedChapters.includes(id)
        ? s.selectedChapters.filter((c) => c !== id)
        : [...s.selectedChapters, id],
    })),

  selectAllChapters: () =>
    set((s) => ({
      selectedChapters: s.metadata?.chapters.map((ch) => ch.id) ?? [],
    })),

  clearBook: () =>
    set({
      bookId: null,
      metadata: null,
      selectedChapters: [],
      error: null,
    }),
}));
