import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/shared/Button";

interface AudioRecorderProps {
  onRecorded: (blob: Blob) => void;
}

export function AudioRecorder({ onRecorded }: AudioRecorderProps) {
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup object URL on unmount or new recording
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
        // Stop all tracks to release microphone
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setRecording(true);
      setElapsed(0);
      setAudioBlob(null);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);

      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } catch {
      setError("Microphone access denied. Please allow microphone access and try again.");
    }
  }, [audioUrl]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRecording(false);
  }, []);

  const handleRetake = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setElapsed(0);
  }, [audioUrl]);

  const handleUse = useCallback(() => {
    if (audioBlob) onRecorded(audioBlob);
  }, [audioBlob, onRecorded]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col gap-2">
      {error && <p className="text-xs text-red-400">{error}</p>}

      {!recording && !audioBlob && (
        <Button variant="secondary" size="sm" onClick={startRecording}>
          Record Audio
        </Button>
      )}

      {recording && (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm text-text-primary font-medium">
              Recording {formatTime(elapsed)}
            </span>
          </div>
          <Button variant="secondary" size="sm" onClick={stopRecording}>
            Stop
          </Button>
        </div>
      )}

      {audioUrl && !recording && (
        <div className="flex flex-col gap-2">
          <audio src={audioUrl} controls className="w-full h-8" />
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleRetake}>
              Retake
            </Button>
            <Button variant="primary" size="sm" onClick={handleUse}>
              Use This
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
