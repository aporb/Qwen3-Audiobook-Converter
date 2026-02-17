import { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { useAudioStore } from "@/stores/useAudioStore";

interface UseWaveSurferOptions {
  container: string | HTMLElement;
  url?: string | null;
}

export function useWaveSurfer({ container, url }: UseWaveSurferOptions) {
  const wsRef = useRef<WaveSurfer | null>(null);
  const [ready, setReady] = useState(false);
  const setPlaying = useAudioStore((s) => s.setPlaying);
  const setCurrentTime = useAudioStore((s) => s.setCurrentTime);
  const setDuration = useAudioStore((s) => s.setDuration);

  useEffect(() => {
    if (!container) return;

    const ws = WaveSurfer.create({
      container,
      url: url ?? undefined,
      waveColor: "rgba(255, 255, 255, 0.2)",
      progressColor: "rgba(255, 255, 255, 0.6)",
      cursorColor: "rgba(255, 255, 255, 0.4)",
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      height: 64,
      normalize: true,
    });

    ws.on("ready", () => {
      setReady(true);
      setDuration(ws.getDuration());
    });

    ws.on("timeupdate", (time) => setCurrentTime(time));
    ws.on("play", () => setPlaying(true));
    ws.on("pause", () => setPlaying(false));
    ws.on("finish", () => setPlaying(false));

    wsRef.current = ws;

    return () => {
      ws.destroy();
      wsRef.current = null;
      setReady(false);
    };
  }, [container, url, setPlaying, setCurrentTime, setDuration]);

  // Load URL when it changes
  useEffect(() => {
    if (wsRef.current && url) {
      setReady(false);
      wsRef.current.load(url);
    }
  }, [url]);

  return {
    wavesurfer: wsRef.current,
    ready,
    play: () => wsRef.current?.play(),
    pause: () => wsRef.current?.pause(),
    playPause: () => wsRef.current?.playPause(),
    setRate: (rate: number) => wsRef.current?.setPlaybackRate(rate),
  };
}
