import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  // Landing / onboarding
  hasSeenLanding: boolean;
  hasCompletedOnboarding: boolean;

  // License
  licenseKey: string | null;
  licenseType: "annual" | "lifetime" | null;
  licenseValid: boolean;
  licenseExpiresAt: string | null;

  // User keys
  openaiApiKey: string | null;

  // Session
  sessionId: string;

  // Deployment
  deploymentMode: "local" | "cloud";

  // Actions
  setHasSeenLanding: (v: boolean) => void;
  setHasCompletedOnboarding: (v: boolean) => void;
  setLicense: (key: string, type: "annual" | "lifetime", expiresAt: string | null) => void;
  clearLicense: () => void;
  setLicenseValid: (v: boolean) => void;
  setOpenaiApiKey: (key: string | null) => void;
  setDeploymentMode: (mode: "local" | "cloud") => void;
}

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback
  return "xxxx-xxxx-xxxx".replace(/x/g, () =>
    Math.floor(Math.random() * 16).toString(16),
  );
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      hasSeenLanding: false,
      hasCompletedOnboarding: false,
      licenseKey: null,
      licenseType: null,
      licenseValid: false,
      licenseExpiresAt: null,
      openaiApiKey: null,
      sessionId: generateSessionId(),
      deploymentMode: "local",

      setHasSeenLanding: (v) => set({ hasSeenLanding: v }),
      setHasCompletedOnboarding: (v) => set({ hasCompletedOnboarding: v }),

      setLicense: (key, type, expiresAt) =>
        set({
          licenseKey: key,
          licenseType: type,
          licenseValid: true,
          licenseExpiresAt: expiresAt,
        }),

      clearLicense: () =>
        set({
          licenseKey: null,
          licenseType: null,
          licenseValid: false,
          licenseExpiresAt: null,
        }),

      setLicenseValid: (v) => set({ licenseValid: v }),
      setOpenaiApiKey: (key) => set({ openaiApiKey: key }),
      setDeploymentMode: (mode) => set({ deploymentMode: mode }),
    }),
    {
      name: "voxcraft-app",
      partialize: (state) => ({
        hasSeenLanding: state.hasSeenLanding,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
        licenseKey: state.licenseKey,
        licenseType: state.licenseType,
        licenseValid: state.licenseValid,
        licenseExpiresAt: state.licenseExpiresAt,
        openaiApiKey: state.openaiApiKey,
        sessionId: state.sessionId,
        // deploymentMode is detected from backend, not persisted
      }),
    },
  ),
);
