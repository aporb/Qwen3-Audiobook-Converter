export interface TourStep {
  targetSelector: string;
  title: string;
  description: string;
  route: string;
  position: "top" | "bottom" | "left" | "right";
}

export const tourSteps: TourStep[] = [
  {
    targetSelector: '[data-tour="engine-toggle"]',
    title: "Choose Your Engine",
    description:
      "Privacy Mode uses local AI (MLX) — your text never leaves your device. Studio Mode uses OpenAI for higher quality voices.",
    route: "/",
    position: "left",
  },
  {
    targetSelector: '[data-tour="quickclip-textarea"]',
    title: "Quick Clip",
    description:
      "Paste any text here for instant text-to-speech. Great for previewing voices or generating short clips.",
    route: "/",
    position: "bottom",
  },
  {
    targetSelector: '[data-tour="voice-selector"]',
    title: "Voice Selection",
    description:
      "Pick a speaker, language, and voice mode. Each engine has its own set of voices.",
    route: "/",
    position: "bottom",
  },
  {
    targetSelector: '[data-tour="perform-button"]',
    title: "Hit Perform",
    description:
      "Click Perform (or Ctrl+Enter) to generate audio. Progress streams in real-time.",
    route: "/",
    position: "top",
  },
  {
    targetSelector: '[data-tour="studio-editor"]',
    title: "Studio Editor",
    description:
      "A rich text editor for longer content. Select a passage and perform just that section.",
    route: "/studio",
    position: "bottom",
  },
  {
    targetSelector: '[data-tour="book-uploader"]',
    title: "Upload a Book",
    description:
      "Drop an EPUB, PDF, or TXT file to start a full audiobook conversion.",
    route: "/audiobook",
    position: "bottom",
  },
];
