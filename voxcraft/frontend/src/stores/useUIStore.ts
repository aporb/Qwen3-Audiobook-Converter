import { create } from "zustand";

type SidebarContext = "settings" | "voice" | "audio";

interface DynamicIslandState {
  visible: boolean;
  label: string;
  progress: number;
}

interface UIState {
  sidebarContext: SidebarContext;
  sidebarOpen: boolean;
  island: DynamicIslandState;

  setSidebarContext: (ctx: SidebarContext) => void;
  toggleSidebar: () => void;
  showIsland: (label: string, progress?: number) => void;
  updateIsland: (progress: number, label?: string) => void;
  hideIsland: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarContext: "settings",
  sidebarOpen: true,
  island: { visible: false, label: "", progress: 0 },

  setSidebarContext: (ctx) => set({ sidebarContext: ctx }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  showIsland: (label, progress = 0) =>
    set({ island: { visible: true, label, progress } }),

  updateIsland: (progress, label) =>
    set((s) => ({
      island: {
        ...s.island,
        progress,
        ...(label !== undefined ? { label } : {}),
      },
    })),

  hideIsland: () =>
    set({ island: { visible: false, label: "", progress: 0 } }),
}));
