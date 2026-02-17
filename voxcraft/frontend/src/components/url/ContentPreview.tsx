import { useState } from "react";
import { clsx } from "clsx";
import { Button } from "@/components/shared/Button";
import type { URLContent } from "@/stores/useURLReaderStore";

interface ContentPreviewProps {
  content: URLContent;
  onEdit?: (content: string) => void;
  onModeChange?: (mode: "full_article" | "summary_insights") => void;
  selectedMode: "full_article" | "summary_insights";
  isEditing?: boolean;
}

export function ContentPreview({
  content,
  onEdit,
  onModeChange,
  selectedMode,
  isEditing = false,
}: ContentPreviewProps) {
  const [editedContent, setEditedContent] = useState(content.content);
  const [isEditMode, setIsEditMode] = useState(false);

  const handleSaveEdit = () => {
    onEdit?.(editedContent);
    setIsEditMode(false);
  };

  const handleCancelEdit = () => {
    setEditedContent(content.content);
    setIsEditMode(false);
  };

  const formatDuration = (minutes: number): string => {
    if (minutes < 1) {
      return `${Math.round(minutes * 60)} sec`;
    }
    return `${Math.round(minutes)} min`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-glass-border pb-4">
        <h2 className="text-xl font-semibold text-text-primary mb-2">
          {content.title}
        </h2>
        <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
          {content.author && (
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              {content.author}
            </span>
          )}
          {content.published_date && (
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {content.published_date}
            </span>
          )}
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {content.word_count.toLocaleString()} words
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            ~{formatDuration(content.estimated_duration_min)} audio
          </span>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-text-primary">
          How would you like this processed?
        </label>
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => onModeChange?.("full_article")}
            className={clsx(
              "p-4 text-left border rounded-xl transition-all duration-200",
              selectedMode === "full_article"
                ? "border-white/30 bg-white/10"
                : "border-glass-border hover:border-white/20 hover:bg-white/5"
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="font-medium text-text-primary">Full Article</span>
            </div>
            <p className="text-sm text-text-secondary">
              Read the complete article word-for-word
            </p>
          </button>

          <button
            type="button"
            onClick={() => onModeChange?.("summary_insights")}
            className={clsx(
              "p-4 text-left border rounded-xl transition-all duration-200",
              selectedMode === "summary_insights"
                ? "border-white/30 bg-white/10"
                : "border-glass-border hover:border-white/20 hover:bg-white/5"
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="font-medium text-text-primary">Summary + Insights</span>
            </div>
            <p className="text-sm text-text-secondary">
              Get a concise summary with key takeaways
            </p>
          </button>
        </div>
      </div>

      {/* Content Editor */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-text-primary">
            Content Preview
          </label>
          {!isEditMode ? (
            <button
              type="button"
              onClick={() => setIsEditMode(true)}
              className="text-sm text-text-secondary hover:text-text-primary flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCancelEdit}
                className="text-sm text-text-secondary hover:text-text-primary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                className="text-sm text-green-400 hover:text-green-300"
              >
                Save
              </button>
            </div>
          )}
        </div>

        {isEditMode ? (
          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            className="w-full h-64 p-4 text-sm bg-surface border border-glass-border rounded-xl text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-white/20 focus:border-white/30 resize-y font-mono leading-relaxed"
            placeholder="Edit the content here..."
          />
        ) : (
          <div className="w-full h-64 p-4 text-sm bg-surface/50 border border-glass-border rounded-xl text-text-primary overflow-y-auto leading-relaxed whitespace-pre-wrap">
            {content.content}
          </div>
        )}
      </div>

      {/* Source Link */}
      <div className="pt-4 border-t border-glass-border">
        <a
          href={content.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          View original article
        </a>
      </div>
    </div>
  );
}
