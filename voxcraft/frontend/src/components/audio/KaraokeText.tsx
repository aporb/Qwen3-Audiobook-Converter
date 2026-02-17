import { useMemo } from "react";
import { clsx } from "clsx";

interface KaraokeTextProps {
  text: string;
  currentTime: number;
  duration: number;
}

export function KaraokeText({ text, currentTime, duration }: KaraokeTextProps) {
  const words = useMemo(() => text.split(/\s+/).filter(Boolean), [text]);
  const totalWords = words.length;
  const wordsPerSecond = duration > 0 ? totalWords / duration : 0;
  const currentWordIndex = Math.floor(currentTime * wordsPerSecond);

  return (
    <div className="text-sm leading-relaxed">
      {words.map((word, i) => (
        <span
          key={i}
          className={clsx(
            "inline transition-colors duration-150",
            i < currentWordIndex
              ? "text-white/60"
              : i === currentWordIndex
                ? "text-text-primary font-semibold"
                : "text-text-muted",
          )}
        >
          {word}{" "}
        </span>
      ))}
    </div>
  );
}
