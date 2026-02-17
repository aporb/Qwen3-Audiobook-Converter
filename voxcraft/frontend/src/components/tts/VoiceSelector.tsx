import { Dropdown } from "@/components/shared/Dropdown";
import { VoiceDesignInput } from "@/components/voice/VoiceDesignInput";
import { VoiceClonePanel } from "@/components/voice/VoiceClonePanel";
import { ModelRequiredBanner } from "@/components/voice/ModelRequiredBanner";
import { useEngineStore } from "@/stores/useEngineStore";
import {
  MLX_SPEAKERS,
  MLX_VOICE_MODES,
  MLX_LANGUAGES,
  OPENAI_VOICES,
  OPENAI_MODELS,
} from "@/lib/constants";
import { clsx } from "clsx";

interface VoiceSelectorProps {
  // MLX
  voiceMode: string;
  onVoiceModeChange: (v: string) => void;
  speaker: string;
  onSpeakerChange: (v: string) => void;
  language: string;
  onLanguageChange: (v: string) => void;
  // OpenAI
  openaiVoice: string;
  onOpenaiVoiceChange: (v: string) => void;
  openaiModel: string;
  onOpenaiModelChange: (v: string) => void;
  // Voice Design
  voiceDescription: string;
  onVoiceDescriptionChange: (v: string) => void;
  // Voice Clone
  selectedVoiceId: string | null;
  onSelectVoice: (id: string | null, audioPath: string, refText: string) => void;
}

export function VoiceSelector({
  voiceMode,
  onVoiceModeChange,
  speaker,
  onSpeakerChange,
  language,
  onLanguageChange,
  openaiVoice,
  onOpenaiVoiceChange,
  openaiModel,
  onOpenaiModelChange,
  voiceDescription,
  onVoiceDescriptionChange,
  selectedVoiceId,
  onSelectVoice,
}: VoiceSelectorProps) {
  const engine = useEngineStore((s) => s.engine);

  return (
    <div className="flex flex-col gap-3" data-tour="voice-selector">
      {/* Voice Mode Selector — always visible */}
      <div>
        <span className="text-xs text-text-muted font-medium block mb-1.5">Voice Mode</span>
        <div className="flex gap-1.5">
          {MLX_VOICE_MODES.map((mode) => {
            const disabled = engine === "openai" && mode.value !== "custom_voice";
            return (
              <button
                key={mode.value}
                disabled={disabled}
                title={disabled ? "Requires Privacy Mode (MLX engine)" : mode.description}
                onClick={() => onVoiceModeChange(mode.value)}
                className={clsx(
                  "flex-1 py-1.5 text-xs font-medium rounded-lg transition-all border",
                  voiceMode === mode.value
                    ? "bg-white/10 text-white border-white/15"
                    : "text-text-muted hover:text-text-secondary border-transparent",
                  disabled && "opacity-40 cursor-not-allowed hover:text-text-muted",
                )}
              >
                {mode.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Voice — MLX */}
      {voiceMode === "custom_voice" && engine === "mlx" && (
        <>
          <Dropdown
            label="Speaker"
            options={MLX_SPEAKERS.map((s) => ({ value: s, label: s }))}
            value={speaker}
            onChange={onSpeakerChange}
          />
          <Dropdown
            label="Language"
            options={MLX_LANGUAGES.map((l) => ({ value: l, label: l.charAt(0).toUpperCase() + l.slice(1) }))}
            value={language}
            onChange={onLanguageChange}
          />
        </>
      )}

      {/* Custom Voice — OpenAI */}
      {voiceMode === "custom_voice" && engine === "openai" && (
        <>
          <Dropdown
            label="Model"
            options={OPENAI_MODELS.map((m) => ({ value: m.value, label: m.label }))}
            value={openaiModel}
            onChange={onOpenaiModelChange}
          />
          <Dropdown
            label="Voice"
            options={OPENAI_VOICES.map((v) => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1) }))}
            value={openaiVoice}
            onChange={onOpenaiVoiceChange}
          />
        </>
      )}

      {/* Voice Design */}
      {voiceMode === "voice_design" && (
        <>
          <ModelRequiredBanner voiceMode="voice_design" />
          <VoiceDesignInput value={voiceDescription} onChange={onVoiceDescriptionChange} />
          <Dropdown
            label="Language"
            options={MLX_LANGUAGES.map((l) => ({ value: l, label: l.charAt(0).toUpperCase() + l.slice(1) }))}
            value={language}
            onChange={onLanguageChange}
          />
        </>
      )}

      {/* Voice Clone */}
      {voiceMode === "voice_clone" && (
        <>
          <ModelRequiredBanner voiceMode="voice_clone" />
          <VoiceClonePanel
            selectedVoiceId={selectedVoiceId}
            onSelectVoice={onSelectVoice}
          />
          <Dropdown
            label="Language"
            options={MLX_LANGUAGES.map((l) => ({ value: l, label: l.charAt(0).toUpperCase() + l.slice(1) }))}
            value={language}
            onChange={onLanguageChange}
          />
        </>
      )}
    </div>
  );
}
