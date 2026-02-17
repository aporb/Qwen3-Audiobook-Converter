import { useEffect, useRef } from "react";
import { subscribeSSE, type SSEEvent } from "@/lib/api";

export function useSSE(
  path: string | null,
  onEvent: (evt: SSEEvent) => void,
) {
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!path) return;
    esRef.current = subscribeSSE(path, onEvent, () => {
      esRef.current = null;
    });
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [path, onEvent]);
}
