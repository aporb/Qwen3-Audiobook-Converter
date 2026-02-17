import { useEffect, useRef } from "react";
import { useWaveSurfer } from "@/hooks/useWaveSurfer";
import { GlassPanel } from "@/components/shared/GlassPanel";

interface WaveformDisplayProps {
  url: string | null;
  onReady?: () => void;
}

export function WaveformDisplay({ url, onReady }: WaveformDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { ready, playPause } = useWaveSurfer({
    container: containerRef.current!,
    url,
  });

  useEffect(() => {
    if (ready) onReady?.();
  }, [ready, onReady]);

  return (
    <GlassPanel solid className="cursor-pointer" onClick={playPause}>
      <div ref={containerRef} className="w-full min-h-[64px]" />
      {!url && (
        <p className="text-xs text-text-muted text-center py-4">
          No audio yet
        </p>
      )}
    </GlassPanel>
  );
}
