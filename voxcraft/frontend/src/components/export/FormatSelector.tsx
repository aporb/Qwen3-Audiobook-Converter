import { clsx } from "clsx";

interface FormatOption {
  value: string;
  label: string;
  description: string;
}

const formats: FormatOption[] = [
  { value: "wav", label: "WAV", description: "Lossless, highest quality" },
  { value: "mp3", label: "MP3", description: "Compressed, widely compatible" },
  { value: "m4b", label: "M4B", description: "Audiobook format with chapters" },
];

interface FormatSelectorProps {
  value: string;
  onChange: (format: string) => void;
}

export function FormatSelector({ value, onChange }: FormatSelectorProps) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
        Output Format
      </h4>
      <div className="grid grid-cols-3 gap-2">
        {formats.map((fmt) => (
          <button
            key={fmt.value}
            onClick={() => onChange(fmt.value)}
            className={clsx(
              "flex flex-col items-center gap-1 p-3 rounded-lg border transition-all",
              value === fmt.value
                ? "border-white/30 bg-white/10 text-white"
                : "border-glass-border hover:border-white/20 text-text-secondary",
            )}
          >
            <span className="text-sm font-semibold">{fmt.label}</span>
            <span className="text-[10px] text-text-muted">{fmt.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
