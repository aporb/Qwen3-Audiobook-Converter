import { useState, type ChangeEvent, type FormEvent } from "react";
import { clsx } from "clsx";
import { Button } from "@/components/shared/Button";

interface URLInputProps {
  onSubmit: (url: string) => void;
  isLoading?: boolean;
  error?: string | null;
}

export function URLInput({ onSubmit, isLoading, error }: URLInputProps) {
  const [url, setUrl] = useState("");
  const [isValid, setIsValid] = useState(true);

  const validateURL = (value: string): boolean => {
    if (!value) return true;
    try {
      const url = new URL(value);
      return url.protocol === "http:" || url.protocol === "https:";
    } catch {
      return false;
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setUrl(value);
    setIsValid(validateURL(value));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (url && isValid && !isLoading) {
      onSubmit(url);
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
      setIsValid(validateURL(text));
    } catch {
      // Clipboard read failed, ignore
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="space-y-4">
        <div className="relative">
          <input
            type="url"
            value={url}
            onChange={handleChange}
            placeholder="https://example.com/article"
            className={clsx(
              "w-full px-4 py-4 pr-32 text-base bg-surface border rounded-xl",
              "placeholder:text-text-tertiary text-text-primary",
              "focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/30",
              "transition-all duration-200",
              !isValid && "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/20",
              isValid && "border-glass-border"
            )}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={handlePaste}
            className="absolute right-20 top-1/2 -translate-y-1/2 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
            disabled={isLoading}
          >
            Paste
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        <div className="flex items-center justify-between">
          <p className="text-sm text-text-secondary">
            Paste a link to an article, blog post, or any web page
          </p>
          <Button
            type="submit"
            size="lg"
            loading={isLoading}
            disabled={!url || !isValid || isLoading}
          >
            {isLoading ? "Fetching..." : "Fetch Content"}
          </Button>
        </div>
      </div>
    </form>
  );
}
