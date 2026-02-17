import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#09090b",
        surface: "#18181b",
        "surface-alt": "#27272a",
        "text-primary": "#f4f4f5",
        "text-secondary": "#a1a1aa",
        "text-muted": "#52525b",
        "glass-border": "rgba(255,255,255,0.07)",
        "glass-bg": "rgba(255,255,255,0.03)",
        accent: "rgba(255,255,255,0.9)",
        "accent-muted": "rgba(255,255,255,0.5)",
        "accent-subtle": "rgba(255,255,255,0.1)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backdropBlur: {
        glass: "20px",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "island-in": "islandIn 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
        "island-out": "islandOut 0.25s ease-in",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
        "pulse-dot": "pulseDot 1.5s ease-in-out infinite",
        "landing-exit": "landingExit 0.8s cubic-bezier(0.4, 0, 0.2, 1) forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        islandIn: {
          "0%": { opacity: "0", transform: "scale(0.85) translateY(-4px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        islandOut: {
          "0%": { opacity: "1", transform: "scale(1)" },
          "100%": { opacity: "0", transform: "scale(0.9)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 8px rgba(255, 255, 255, 0.15)" },
          "50%": { boxShadow: "0 0 20px rgba(255, 255, 255, 0.3)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        landingExit: {
          "0%": { opacity: "1", transform: "translateY(0)" },
          "100%": { opacity: "0", transform: "translateY(-100%)" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
