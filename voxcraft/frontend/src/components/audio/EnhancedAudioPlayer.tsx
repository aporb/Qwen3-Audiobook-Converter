import { useRef, useEffect, useState, useCallback } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { useAudioStore } from "@/stores/useAudioStore";
import { useWaveSurfer } from "@/hooks/useWaveSurfer";
import { apiFetch } from "@/lib/api";
import { clsx } from "clsx";

interface EnhancedAudioPlayerProps {
  url: string | null;
  /** Default download format. "mp3" for clips, "m4b" for audiobooks. */
  downloadFormat?: "mp3" | "m4b" | "wav";
}

const PLAYBACK_RATES = [1, 1.25, 1.5, 2] as const;

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function EnhancedAudioPlayer({ url, downloadFormat = "mp3" }: EnhancedAudioPlayerProps) {
  const waveRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [rateIndex, setRateIndex] = useState(0);
  const [isConverting, setIsConverting] = useState(false);
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const currentTime = useAudioStore((s) => s.currentTime);
  const duration = useAudioStore((s) => s.duration);

  // Wait for ref to be attached before creating WaveSurfer
  useEffect(() => {
    if (waveRef.current) setMounted(true);
  }, []);

  const { ready, playPause, setRate } = useWaveSurfer({
    container: mounted ? waveRef.current! : undefined!,
    url,
  });

  const cycleRate = useCallback(() => {
    const nextIndex = (rateIndex + 1) % PLAYBACK_RATES.length;
    const nextRate = PLAYBACK_RATES[nextIndex] ?? 1;
    setRateIndex(nextIndex);
    setRate(nextRate);
  }, [rateIndex, setRate]);

  const handleDownload = useCallback(async () => {
    if (!url) return;

    // Extract file_id from URL: "/api/audio/files/{file_id}"
    const fileId = url.split("/").pop() ?? "";

    if (downloadFormat === "wav") {
      window.open(url, "_blank");
      return;
    }

    setIsConverting(true);
    try {
      const res = await apiFetch<{ download_url: string }>("/export/convert-format", {
        method: "POST",
        body: JSON.stringify({ file_id: fileId, output_format: downloadFormat }),
      });
      window.open(`/api${res.download_url}`, "_blank");
    } catch {
      // Fallback to raw WAV download
      window.open(url, "_blank");
    } finally {
      setIsConverting(false);
    }
  }, [url, downloadFormat]);

  if (!url) return null;

  const currentRate = PLAYBACK_RATES[rateIndex];

  return (
    <GlassPanel solid className="flex flex-col gap-3">
      {/* Waveform */}
      <div
        ref={waveRef}
        className="w-full min-h-[64px] cursor-pointer"
        onClick={playPause}
      />

      {/* Controls */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={playPause} disabled={!ready}>
          {isPlaying ? "\u23F8" : "\u25B6"}
        </Button>
        <span className="text-xs text-text-secondary font-mono tabular-nums">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {/* Speed selector */}
        <button
          onClick={cycleRate}
          disabled={!ready}
          className={clsx(
            "px-2 py-0.5 text-xs font-medium rounded-md transition-all border",
            currentRate === 1
              ? "text-text-muted border-transparent hover:text-text-secondary hover:bg-white/5"
              : "bg-white/10 text-white border-white/15",
            !ready && "opacity-50 cursor-not-allowed",
          )}
          title="Playback speed"
        >
          {currentRate}x
        </button>

        <div className="flex-1" />
        <button
          onClick={handleDownload}
          disabled={isConverting}
          className={clsx(
            "text-xs transition-colors",
            isConverting
              ? "text-text-muted cursor-wait"
              : "text-text-muted hover:text-text-secondary",
          )}
        >
          {isConverting ? "Converting..." : `Download ${downloadFormat.toUpperCase()}`}
        </button>
      </div>
    </GlassPanel>
  );
}
