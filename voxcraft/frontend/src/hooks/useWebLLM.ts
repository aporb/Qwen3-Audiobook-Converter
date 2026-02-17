import { useRef, useState, useCallback, useEffect } from "react";

interface WorkerResponse {
  type: string;
  progress?: number;
  text?: string;
  error?: string;
  chunkIndex?: number;
}

// Module-level singleton: all useWebLLM() instances share ONE worker
let sharedWorker: Worker | null = null;

function getSharedWorker(): Worker {
  if (!sharedWorker) {
    sharedWorker = new Worker(
      new URL("../workers/webllm.worker.ts", import.meta.url),
      { type: "module" },
    );
  }
  return sharedWorker;
}

export function useWebLLM() {
  const [isReady, setIsReady] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadText, setDownloadText] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [webgpuAvailable, setWebgpuAvailable] = useState(false);

  // Pending generate promises keyed by chunkIndex
  const pendingRef = useRef<Map<number, { resolve: (text: string) => void; reject: (err: Error) => void }>>(new Map());

  useEffect(() => {
    setWebgpuAvailable("gpu" in navigator);
  }, []);

  // Register message listener on mount, clean up on unmount.
  // Using addEventListener so multiple hook instances can each receive messages.
  useEffect(() => {
    const worker = getSharedWorker();

    const handler = (e: MessageEvent<WorkerResponse>) => {
      const msg = e.data;

      if (msg.type === "load-progress") {
        setDownloadProgress(msg.progress ?? 0);
        setDownloadText(msg.text ?? "");
      }
      if (msg.type === "load-complete") {
        setIsDownloading(false);
        setIsReady(true);
        setLoadError(null);
      }
      if (msg.type === "load-error") {
        setIsDownloading(false);
        setIsReady(false);
        setLoadError(msg.error ?? "Failed to load model");
      }

      if (msg.type === "generate-complete" && msg.chunkIndex !== undefined) {
        const pending = pendingRef.current.get(msg.chunkIndex);
        if (pending) {
          pending.resolve(msg.text ?? "");
          pendingRef.current.delete(msg.chunkIndex);
        }
      }
      if (msg.type === "generate-error" && msg.chunkIndex !== undefined) {
        const pending = pendingRef.current.get(msg.chunkIndex);
        if (pending) {
          pending.reject(new Error(msg.error ?? "Generation failed"));
          pendingRef.current.delete(msg.chunkIndex);
        }
      }
    };

    worker.addEventListener("message", handler);
    return () => worker.removeEventListener("message", handler);
  }, []);

  const loadModel = useCallback((modelId: string) => {
    setIsDownloading(true);
    setIsReady(false);
    setLoadError(null);
    setDownloadProgress(0);
    setDownloadText("Initializing...");
    getSharedWorker().postMessage({ type: "load", modelId });
  }, []);

  const generate = useCallback((systemPrompt: string, userContent: string, chunkIndex: number): Promise<string> => {
    return new Promise((resolve, reject) => {
      pendingRef.current.set(chunkIndex, { resolve, reject });
      getSharedWorker().postMessage({ type: "generate", systemPrompt, userContent, chunkIndex });
    });
  }, []);

  const abort = useCallback(() => {
    getSharedWorker().postMessage({ type: "abort" });
    // Reject all pending
    for (const [, pending] of pendingRef.current) {
      pending.reject(new Error("Aborted"));
    }
    pendingRef.current.clear();
  }, []);

  return {
    loadModel,
    generate,
    abort,
    isReady,
    isDownloading,
    downloadProgress,
    downloadText,
    loadError,
    webgpuAvailable,
  };
}
