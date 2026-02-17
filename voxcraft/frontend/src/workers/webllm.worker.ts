import { CreateMLCEngine, type MLCEngine, type InitProgressReport } from "@mlc-ai/web-llm";

let engine: MLCEngine | null = null;

interface LoadMessage {
  type: "load";
  modelId: string;
}

interface GenerateMessage {
  type: "generate";
  systemPrompt: string;
  userContent: string;
  chunkIndex: number;
}

interface AbortMessage {
  type: "abort";
}

type WorkerMessage = LoadMessage | GenerateMessage | AbortMessage;

self.onmessage = async (e: MessageEvent<WorkerMessage>) => {
  const msg = e.data;

  if (msg.type === "load") {
    try {
      engine = await CreateMLCEngine(msg.modelId, {
        initProgressCallback: (report: InitProgressReport) => {
          self.postMessage({
            type: "load-progress",
            progress: report.progress,
            text: report.text,
          });
        },
      });
      self.postMessage({ type: "load-complete" });
    } catch (err) {
      console.error("[webllm worker] Model load failed:", err);
      self.postMessage({ type: "load-error", error: String(err) });
    }
  }

  if (msg.type === "generate") {
    if (!engine) {
      self.postMessage({ type: "generate-error", chunkIndex: msg.chunkIndex, error: "Model not loaded" });
      return;
    }
    try {
      const response = await engine.chat.completions.create({
        messages: [
          { role: "system", content: msg.systemPrompt },
          { role: "user", content: msg.userContent },
        ],
        temperature: 0.3,
      });
      const text = response.choices[0]?.message.content ?? msg.userContent;
      self.postMessage({ type: "generate-complete", chunkIndex: msg.chunkIndex, text });
    } catch (err) {
      self.postMessage({ type: "generate-error", chunkIndex: msg.chunkIndex, error: String(err) });
    }
  }

  if (msg.type === "abort") {
    if (engine) {
      engine.resetChat();
    }
  }
};
