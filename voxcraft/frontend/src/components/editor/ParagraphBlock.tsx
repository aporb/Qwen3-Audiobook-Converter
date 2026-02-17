import { clsx } from "clsx";
import { Badge } from "@/components/shared/Badge";

interface ParagraphBlockProps {
  id: string;
  text: string;
  speaker?: string;
  speakerColor?: string;
  isSelected?: boolean;
  onClick?: () => void;
}

export function ParagraphBlock({
  text,
  speaker,
  speakerColor,
  isSelected,
  onClick,
}: ParagraphBlockProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        "px-4 py-2 rounded-lg transition-colors cursor-pointer border",
        isSelected
          ? "border-white/30 bg-white/5"
          : "border-transparent hover:bg-white/3",
        speakerColor && `border-l-2`,
      )}
      style={speakerColor ? { borderLeftColor: speakerColor } : undefined}
    >
      {speaker && (
        <Badge variant="info" className="mb-1">
          {speaker}
        </Badge>
      )}
      <p className="text-sm text-text-primary leading-relaxed">{text}</p>
    </div>
  );
}
