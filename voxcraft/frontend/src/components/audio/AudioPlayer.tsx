import { useRef, useEffect } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { useAudioStore } from "@/stores/useAudioStore";

interface AudioPlayerProps {
  url: string | null;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function AudioPlayer({ url }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const currentTime = useAudioStore((s) => s.currentTime);
  const duration = useAudioStore((s) => s.duration);
  const setPlaying = useAudioStore((s) => s.setPlaying);
  const setCurrentTime = useAudioStore((s) => s.setCurrentTime);
  const setDuration = useAudioStore((s) => s.setDuration);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setCurrentTime(el.currentTime);
    const onMeta = () => setDuration(el.duration);
    const onEnd = () => setPlaying(false);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("ended", onEnd);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("ended", onEnd);
    };
  }, [setCurrentTime, setDuration, setPlaying]);

  const toggle = () => {
    const el = audioRef.current;
    if (!el) return;
    if (isPlaying) {
      el.pause();
      setPlaying(false);
    } else {
      el.play();
      setPlaying(true);
    }
  };

  if (!url) return null;

  return (
    <GlassPanel solid className="flex items-center gap-4">
      <audio ref={audioRef} src={url} preload="metadata" />
      <Button variant="ghost" size="sm" onClick={toggle}>
        {isPlaying ? "⏸" : "▶"}
      </Button>
      <span className="text-xs text-text-secondary font-mono tabular-nums">
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full bg-white/60 rounded-full transition-all"
          style={{ width: duration > 0 ? `${(currentTime / duration) * 100}%` : "0%" }}
        />
      </div>
      <a
        href={url}
        download
        className="text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        Download
      </a>
    </GlassPanel>
  );
}
