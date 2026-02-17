import { useState, useEffect, useCallback } from "react";
import { HeroSection } from "./HeroSection";
import { FeaturesSection } from "./FeaturesSection";
import { HowItWorksSection } from "./HowItWorksSection";
import { CTASection } from "./CTASection";
import { useAppStore } from "@/stores/useAppStore";

export function LandingOverlay() {
  const hasSeenLanding = useAppStore((s) => s.hasSeenLanding);
  const setHasSeenLanding = useAppStore((s) => s.setHasSeenLanding);
  const [exiting, setExiting] = useState(false);
  const [hidden, setHidden] = useState(false);

  // Return visitors: auto-dismiss after 2s
  useEffect(() => {
    if (hasSeenLanding && !hidden) {
      const timer = setTimeout(() => handleExit(), 2000);
      return () => clearTimeout(timer);
    }
  }, [hasSeenLanding, hidden]);

  const handleExit = useCallback(() => {
    setExiting(true);
    setHasSeenLanding(true);
    // Wait for animation to finish
    setTimeout(() => setHidden(true), 800);
  }, [setHasSeenLanding]);

  // Keyboard: Enter or Escape to dismiss
  useEffect(() => {
    if (hidden) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === "Escape") {
        handleExit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [hidden, handleExit]);

  if (hidden) return null;

  return (
    <div
      className={`fixed inset-0 z-[100] overflow-y-auto landing-gradient-mesh ${
        exiting ? "animate-landing-exit" : ""
      }`}
    >
      {/* Skip button for return visitors */}
      {hasSeenLanding && (
        <button
          onClick={handleExit}
          className="fixed top-4 right-4 z-10 text-xs text-text-muted hover:text-text-secondary transition-colors px-3 py-1.5 rounded-lg bg-white/5 backdrop-blur-sm"
        >
          Skip
        </button>
      )}

      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
      <CTASection onEnter={handleExit} />
    </div>
  );
}
