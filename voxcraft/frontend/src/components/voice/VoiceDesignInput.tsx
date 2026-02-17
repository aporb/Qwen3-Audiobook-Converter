import { VOICE_DESIGN_PRESETS } from "@/lib/voice-design-presets";
import { clsx } from "clsx";

interface VoiceDesignInputProps {
  value: string;
  onChange: (v: string) => void;
}

export function VoiceDesignInput({ value, onChange }: VoiceDesignInputProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Preset chips */}
      <div className="flex flex-wrap gap-1.5">
        {VOICE_DESIGN_PRESETS.map((preset) => (
          <button
            key={preset.label}
            onClick={() => onChange(preset.description)}
            className={clsx(
              "px-2.5 py-1 text-xs rounded-full transition-all border",
              value === preset.description
                ? "bg-white/10 text-white border-white/15"
                : "text-text-muted hover:text-text-secondary hover:bg-white/5 border-transparent",
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Textarea */}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Describe the voice you want..."
        rows={3}
        className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted resize-none outline-none"
      />
      <span className="text-xs text-text-muted text-right">
        {value.length} characters
      </span>
    </div>
  );
}
