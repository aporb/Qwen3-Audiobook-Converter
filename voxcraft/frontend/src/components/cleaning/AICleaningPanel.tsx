import { useState, useCallback } from "react";
import { Toggle } from "@/components/shared/Toggle";
import { Button } from "@/components/shared/Button";
import { CleaningPreview } from "./CleaningPreview";
import { BrowserModelManager } from "./BrowserModelManager";
import { useCleaningStore } from "@/stores/useCleaningStore";
import { useWebLLM } from "@/hooks/useWebLLM";
import { CLEANING_PRESETS, CLEANING_BACKENDS } from "@/lib/cleaning-presets";
import { clsx } from "clsx";

interface AICleaningPanelProps {
  sampleText?: string;
}

export function AICleaningPanel({ sampleText }: AICleaningPanelProps) {
  const enabled = useCleaningStore((s) => s.aiCleaningEnabled);
  const setEnabled = useCleaningStore((s) => s.setAiCleaningEnabled);
  const backend = useCleaningStore((s) => s.cleaningBackend);
  const setBackend = useCleaningStore((s) => s.setCleaningBackend);
  const preset = useCleaningStore((s) => s.cleaningPreset);
  const setPreset = useCleaningStore((s) => s.setCleaningPreset);
  const customPrompt = useCleaningStore((s) => s.customPrompt);
  const setCustomPrompt = useCleaningStore((s) => s.setCustomPrompt);
  const customBaseUrl = useCleaningStore((s) => s.customBaseUrl);
  const setCustomBaseUrl = useCleaningStore((s) => s.setCustomBaseUrl);
  const customModel = useCleaningStore((s) => s.customModel);
  const setCustomModel = useCleaningStore((s) => s.setCustomModel);
  const customApiKey = useCleaningStore((s) => s.customApiKey);
  const setCustomApiKey = useCleaningStore((s) => s.setCustomApiKey);
  const previewClean = useCleaningStore((s) => s.previewClean);
  const browserModelReady = useCleaningStore((s) => s.browserModelReady);
  const error = useCleaningStore((s) => s.error);

  const { generate: browserGenerate } = useWebLLM();

  const [previewing, setPreviewing] = useState(false);

  const handlePreview = useCallback(async () => {
    if (!sampleText?.trim()) return;
    setPreviewing(true);
    try {
      await previewClean(sampleText, browserGenerate);
    } finally {
      setPreviewing(false);
    }
  }, [sampleText, previewClean, browserGenerate]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          AI Text Cleaning
        </h4>
        <Toggle checked={enabled} onChange={setEnabled} />
      </div>

      {enabled && (
        <div className="flex flex-col gap-3 animate-slide-up">
          {/* Backend selector */}
          <div className="flex gap-1.5">
            {CLEANING_BACKENDS.map((b) => (
              <button
                key={b.value}
                onClick={() => setBackend(b.value)}
                className={clsx(
                  "flex-1 py-1.5 text-xs font-medium rounded-lg transition-all",
                  backend === b.value
                    ? "bg-white/10 text-white border border-white/15"
                    : "text-text-muted hover:text-text-secondary border border-transparent",
                )}
              >
                {b.label}
              </button>
            ))}
          </div>

          {/* Preset selector */}
          <div className="flex flex-col gap-1.5">
            {CLEANING_PRESETS.map((p) => (
              <label
                key={p.value}
                className={clsx(
                  "flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-all",
                  preset === p.value
                    ? "bg-white/10 border border-white/15"
                    : "hover:bg-white/5 border border-transparent",
                )}
              >
                <input
                  type="radio"
                  name="cleaning-preset"
                  value={p.value}
                  checked={preset === p.value}
                  onChange={() => setPreset(p.value)}
                  className="mt-0.5 accent-white"
                />
                <div>
                  <span className="text-sm text-text-primary">{p.label}</span>
                  <p className="text-xs text-text-muted">{p.description}</p>
                </div>
              </label>
            ))}
          </div>

          {/* Custom prompt textarea */}
          {preset === "custom" && (
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Enter your cleaning instructions..."
              rows={4}
              className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted resize-none outline-none"
            />
          )}

          {/* Backend-specific config */}
          {backend === "openai" && (
            <p className="text-xs text-text-muted">
              Uses your OpenAI API key from Settings. Model: gpt-4o-mini.
            </p>
          )}

          {backend === "custom" && (
            <div className="flex flex-col gap-2">
              <input
                type="text"
                value={customBaseUrl}
                onChange={(e) => setCustomBaseUrl(e.target.value)}
                placeholder="Base URL (e.g. http://localhost:11434/v1)"
                className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
              />
              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="Model name (e.g. llama3.1)"
                className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
              />
              <input
                type="password"
                value={customApiKey}
                onChange={(e) => setCustomApiKey(e.target.value)}
                placeholder="API key (optional)"
                className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
              />
            </div>
          )}

          {backend === "browser" && (
            <BrowserModelManager />
          )}

          {/* Preview */}
          {(backend !== "browser" || browserModelReady) && sampleText && (
            <Button
              variant="ghost"
              size="sm"
              loading={previewing}
              onClick={handlePreview}
              disabled={!sampleText?.trim()}
            >
              Preview Cleaning
            </Button>
          )}

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}

          <CleaningPreview />
        </div>
      )}
    </div>
  );
}

