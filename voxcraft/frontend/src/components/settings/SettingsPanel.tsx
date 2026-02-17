import { useState, useCallback } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Badge } from "@/components/shared/Badge";
import { Toggle } from "@/components/shared/Toggle";
import { Dropdown } from "@/components/shared/Dropdown";
import { ApiKeyInput } from "./ApiKeyInput";
import { AICleaningPanel } from "@/components/cleaning/AICleaningPanel";
import { useAppStore } from "@/stores/useAppStore";
import { usePreferencesStore } from "@/stores/usePreferencesStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { apiFetch } from "@/lib/api";
import {
  MLX_SPEAKERS,
  MLX_VOICE_MODES,
  MLX_LANGUAGES,
} from "@/lib/constants";

export function SettingsPanel() {
  const openaiApiKey = useAppStore((s) => s.openaiApiKey);
  const setOpenaiApiKey = useAppStore((s) => s.setOpenaiApiKey);
  const licenseKey = useAppStore((s) => s.licenseKey);
  const licenseType = useAppStore((s) => s.licenseType);
  const licenseValid = useAppStore((s) => s.licenseValid);
  const deploymentMode = useAppStore((s) => s.deploymentMode);
  const setHasCompletedOnboarding = useAppStore((s) => s.setHasCompletedOnboarding);

  const engine = useEngineStore((s) => s.engine);
  const setEngine = useEngineStore((s) => s.setEngine);

  const prefs = usePreferencesStore();

  const [keyStatus, setKeyStatus] = useState<"idle" | "testing" | "valid" | "invalid">(
    openaiApiKey ? "idle" : "idle",
  );

  const handleTestKey = useCallback(async () => {
    setKeyStatus("testing");
    try {
      const res = await apiFetch<{ valid: boolean; error?: string }>(
        "/system/validate-openai-key",
        { method: "POST" },
      );
      setKeyStatus(res.valid ? "valid" : "invalid");
    } catch {
      setKeyStatus("invalid");
    }
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* License */}
      <GlassPanel solid>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          License
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Status</span>
          <Badge variant={licenseValid ? "active" : "inactive"} dot>
            {licenseValid
              ? licenseType === "lifetime"
                ? "Lifetime"
                : "Annual"
              : "Not activated"}
          </Badge>
        </div>
        {licenseKey && (
          <p className="text-xs text-text-muted mt-2 font-mono">
            {licenseKey.slice(0, 8)}{"\u2022".repeat(8)}{licenseKey.slice(-4)}
          </p>
        )}
      </GlassPanel>

      {/* OpenAI Key */}
      <GlassPanel solid>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          OpenAI API Key
        </h3>
        <ApiKeyInput
          value={openaiApiKey ?? ""}
          onChange={(v) => {
            setOpenaiApiKey(v || null);
            setKeyStatus("idle");
          }}
          onTest={handleTestKey}
          status={keyStatus}
        />
        <p className="text-xs text-text-muted mt-2">
          Required for Studio Mode TTS and casting analysis.
          {deploymentMode === "local" && " Falls back to OPENAI_API_KEY env var."}
        </p>
      </GlassPanel>

      {/* Engine Default */}
      {deploymentMode === "local" && (
        <GlassPanel solid>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Default Engine
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => setEngine("mlx")}
              className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${
                engine === "mlx"
                  ? "bg-white/10 text-white border border-white/15"
                  : "text-text-muted hover:text-text-secondary border border-transparent"
              }`}
            >
              Privacy Mode
            </button>
            <button
              onClick={() => setEngine("openai")}
              className={`flex-1 py-2 text-xs font-medium rounded-lg transition-all ${
                engine === "openai"
                  ? "bg-white/10 text-white border border-white/15"
                  : "text-text-muted hover:text-text-secondary border border-transparent"
              }`}
            >
              Studio Mode
            </button>
          </div>
        </GlassPanel>
      )}

      {/* Voice Defaults */}
      <GlassPanel solid>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Voice Defaults
        </h3>
        <div className="flex flex-col gap-3">
          <Dropdown
            label="Voice Mode"
            options={MLX_VOICE_MODES.map((m) => ({ value: m.value, label: m.label }))}
            value={prefs.voiceMode}
            onChange={prefs.setVoiceMode}
          />
          <Dropdown
            label="Speaker"
            options={MLX_SPEAKERS.map((s) => ({ value: s, label: s }))}
            value={prefs.speaker}
            onChange={prefs.setSpeaker}
          />
          <Dropdown
            label="Language"
            options={MLX_LANGUAGES.map((l) => ({ value: l, label: l.charAt(0).toUpperCase() + l.slice(1) }))}
            value={prefs.language}
            onChange={prefs.setLanguage}
          />
        </div>
      </GlassPanel>

      {/* Text Processing Defaults */}
      <GlassPanel solid>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          Text Processing
        </h3>
        <div className="flex flex-col gap-3">
          <Toggle checked={prefs.fixCapitals} onChange={prefs.setFixCapitals} label="Fix capitals" />
          <Toggle checked={prefs.removeFootnotes} onChange={prefs.setRemoveFootnotes} label="Remove footnotes" />
          <Toggle checked={prefs.normalizeChars} onChange={prefs.setNormalizeChars} label="Normalize characters" />
        </div>
      </GlassPanel>

      {/* AI Text Cleaning */}
      <GlassPanel solid>
        <AICleaningPanel />
      </GlassPanel>

      {/* About */}
      <GlassPanel solid>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
          About
        </h3>
        <div className="flex flex-col gap-1 text-xs text-text-secondary">
          <div className="flex justify-between">
            <span>Version</span>
            <span className="text-text-muted">2.0.0</span>
          </div>
          <div className="flex justify-between">
            <span>Mode</span>
            <span className="text-text-muted capitalize">{deploymentMode}</span>
          </div>
        </div>
        <button
          onClick={() => setHasCompletedOnboarding(false)}
          className="mt-3 text-xs text-white/60 hover:text-white transition-colors"
        >
          Re-run onboarding tour
        </button>
      </GlassPanel>
    </div>
  );
}
