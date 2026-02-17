import { Toggle } from "@/components/shared/Toggle";
import { AICleaningPanel } from "@/components/cleaning/AICleaningPanel";

interface TextProcessingProps {
  fixCapitals: boolean;
  onFixCapitals: (v: boolean) => void;
  removeFootnotes: boolean;
  onRemoveFootnotes: (v: boolean) => void;
  normalizeChars: boolean;
  onNormalizeChars: (v: boolean) => void;
  sampleText?: string;
}

export function TextProcessing({
  fixCapitals,
  onFixCapitals,
  removeFootnotes,
  onRemoveFootnotes,
  normalizeChars,
  onNormalizeChars,
  sampleText,
}: TextProcessingProps) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
        Text Cleaning
      </h4>
      <Toggle checked={fixCapitals} onChange={onFixCapitals} label="Fix spaced capitals" />
      <Toggle
        checked={removeFootnotes}
        onChange={onRemoveFootnotes}
        label="Remove footnotes"
      />
      <Toggle
        checked={normalizeChars}
        onChange={onNormalizeChars}
        label="Normalize special chars"
      />

      <div className="border-t border-glass-border mt-2 pt-3">
        <AICleaningPanel sampleText={sampleText} />
      </div>
    </div>
  );
}
