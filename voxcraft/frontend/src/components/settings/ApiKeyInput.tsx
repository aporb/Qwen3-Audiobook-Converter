import { useState } from "react";
import { clsx } from "clsx";

interface ApiKeyInputProps {
  value: string;
  onChange: (value: string) => void;
  onTest?: () => void;
  status?: "idle" | "testing" | "valid" | "invalid";
  placeholder?: string;
}

export function ApiKeyInput({
  value,
  onChange,
  onTest,
  status = "idle",
  placeholder = "sk-...",
}: ApiKeyInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <div className="relative flex items-center">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-surface border border-glass-border rounded-lg px-3 py-2 pr-20 text-sm text-text-primary placeholder:text-text-muted font-mono"
        />
        <div className="absolute right-2 flex items-center gap-1">
          {/* Show/hide toggle */}
          <button
            type="button"
            onClick={() => setVisible(!visible)}
            className="p-1 text-text-muted hover:text-text-secondary transition-colors"
            title={visible ? "Hide" : "Show"}
          >
            {visible ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
          {/* Status dot */}
          {status !== "idle" && (
            <span
              className={clsx(
                "w-2 h-2 rounded-full",
                status === "testing" && "bg-white/50 animate-pulse-dot",
                status === "valid" && "bg-white",
                status === "invalid" && "bg-white/30",
              )}
            />
          )}
        </div>
      </div>
      {onTest && value && (
        <button
          type="button"
          onClick={onTest}
          disabled={status === "testing"}
          className="self-start text-xs text-white/60 hover:text-white transition-colors disabled:opacity-50"
        >
          {status === "testing" ? "Testing..." : "Test Key"}
        </button>
      )}
    </div>
  );
}
