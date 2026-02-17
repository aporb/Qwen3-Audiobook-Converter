import { useCallback, useRef, useState } from "react";
import { clsx } from "clsx";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { useProjectStore } from "@/stores/useProjectStore";

export function BookUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const isUploading = useProjectStore((s) => s.isUploading);
  const uploadBook = useProjectStore((s) => s.uploadBook);

  const handleFile = useCallback(
    (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!ext || !["epub", "pdf", "txt"].includes(ext)) return;
      uploadBook(file);
    },
    [uploadBook],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <GlassPanel
      solid
      data-tour="book-uploader"
      className={clsx(
        "border-2 border-dashed cursor-pointer transition-colors text-center",
        dragOver
          ? "border-white/40 bg-white/5"
          : "border-glass-border hover:border-white/20",
        isUploading && "opacity-60 pointer-events-none",
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".epub,.pdf,.txt"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      <div className="py-8">
        <div className="text-3xl mb-2">
          {isUploading ? "⏳" : "📖"}
        </div>
        <p className="text-sm text-text-secondary">
          {isUploading
            ? "Uploading and analyzing..."
            : "Drop an EPUB, PDF, or TXT file here"}
        </p>
        <p className="text-xs text-text-muted mt-1">or click to browse</p>
      </div>
    </GlassPanel>
  );
}
