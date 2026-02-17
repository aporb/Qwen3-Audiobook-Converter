import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAppStore } from "@/stores/useAppStore";
import { tourSteps } from "./tourSteps";

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

export function TourOverlay() {
  const hasCompletedOnboarding = useAppStore((s) => s.hasCompletedOnboarding);
  const hasSeenLanding = useAppStore((s) => s.hasSeenLanding);
  const setHasCompletedOnboarding = useAppStore((s) => s.setHasCompletedOnboarding);

  const navigate = useNavigate();
  const location = useLocation();
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<Rect | null>(null);
  const [active, setActive] = useState(false);
  const retryRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Only show if landing dismissed and onboarding not completed
  useEffect(() => {
    if (hasSeenLanding && !hasCompletedOnboarding) {
      // Small delay to let the app render after landing dismiss
      const timer = setTimeout(() => setActive(true), 1000);
      return () => clearTimeout(timer);
    }
    setActive(false);
  }, [hasSeenLanding, hasCompletedOnboarding]);

  const step = tourSteps[stepIndex];

  // Navigate to step route and find target element
  useEffect(() => {
    if (!active || !step) return;

    if (location.pathname !== step.route) {
      navigate(step.route);
    }

    const findTarget = () => {
      const el = document.querySelector(step.targetSelector);
      if (el) {
        const rect = el.getBoundingClientRect();
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
        });
      } else {
        setTargetRect(null);
      }
    };

    // Retry a few times in case the element isn't rendered yet
    findTarget();
    retryRef.current = setTimeout(findTarget, 300);
    const retry2 = setTimeout(findTarget, 600);

    const handleResize = () => findTarget();
    window.addEventListener("resize", handleResize);

    return () => {
      clearTimeout(retryRef.current);
      clearTimeout(retry2);
      window.removeEventListener("resize", handleResize);
    };
  }, [active, step, stepIndex, location.pathname, navigate]);

  const handleNext = useCallback(() => {
    if (stepIndex < tourSteps.length - 1) {
      setStepIndex((i) => i + 1);
    } else {
      setHasCompletedOnboarding(true);
    }
  }, [stepIndex, setHasCompletedOnboarding]);

  const handleSkip = useCallback(() => {
    setHasCompletedOnboarding(true);
  }, [setHasCompletedOnboarding]);

  if (!active || !step) return null;

  // Calculate tooltip position
  const pad = 12;
  const tooltipStyle: React.CSSProperties = {};
  if (targetRect) {
    switch (step.position) {
      case "bottom":
        tooltipStyle.top = targetRect.top + targetRect.height + pad;
        tooltipStyle.left = targetRect.left + targetRect.width / 2;
        tooltipStyle.transform = "translateX(-50%)";
        break;
      case "top":
        tooltipStyle.bottom = window.innerHeight - targetRect.top + pad;
        tooltipStyle.left = targetRect.left + targetRect.width / 2;
        tooltipStyle.transform = "translateX(-50%)";
        break;
      case "left":
        tooltipStyle.top = targetRect.top + targetRect.height / 2;
        tooltipStyle.right = window.innerWidth - targetRect.left + pad;
        tooltipStyle.transform = "translateY(-50%)";
        break;
      case "right":
        tooltipStyle.top = targetRect.top + targetRect.height / 2;
        tooltipStyle.left = targetRect.left + targetRect.width + pad;
        tooltipStyle.transform = "translateY(-50%)";
        break;
    }
  } else {
    // Fallback: center on screen
    tooltipStyle.top = "50%";
    tooltipStyle.left = "50%";
    tooltipStyle.transform = "translate(-50%, -50%)";
  }

  return (
    <div className="fixed inset-0 z-[80]">
      {/* Dim overlay with spotlight cutout */}
      {targetRect ? (
        <div
          className="absolute rounded-lg transition-all duration-300"
          style={{
            top: targetRect.top - 4,
            left: targetRect.left - 4,
            width: targetRect.width + 8,
            height: targetRect.height + 8,
            boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.6)",
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-black/60" />
      )}

      {/* Tooltip */}
      <div
        className="absolute glass-panel-solid p-4 max-w-xs animate-slide-up"
        style={tooltipStyle}
      >
        <h3 className="text-sm font-semibold text-text-primary mb-1">{step.title}</h3>
        <p className="text-xs text-text-secondary leading-relaxed mb-3">
          {step.description}
        </p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-text-muted">
            {stepIndex + 1} / {tourSteps.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleSkip}
              className="text-xs text-text-muted hover:text-text-secondary transition-colors px-2 py-1"
            >
              Skip
            </button>
            <button
              onClick={handleNext}
              className="text-xs font-medium text-black bg-white px-3 py-1 rounded-lg hover:bg-white/90"
            >
              {stepIndex < tourSteps.length - 1 ? "Next" : "Done"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
