import type { Editor } from "@tiptap/react";
import { clsx } from "clsx";

interface EditorToolbarProps {
  editor: Editor;
}

interface ToolbarButton {
  label: string;
  icon: string;
  action: () => void;
  isActive: () => boolean;
}

export function EditorToolbar({ editor }: EditorToolbarProps) {
  const buttons: ToolbarButton[] = [
    {
      label: "Bold",
      icon: "B",
      action: () => editor.chain().focus().toggleBold().run(),
      isActive: () => editor.isActive("bold"),
    },
    {
      label: "Italic",
      icon: "I",
      action: () => editor.chain().focus().toggleItalic().run(),
      isActive: () => editor.isActive("italic"),
    },
    {
      label: "Heading 1",
      icon: "H1",
      action: () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
      isActive: () => editor.isActive("heading", { level: 1 }),
    },
    {
      label: "Heading 2",
      icon: "H2",
      action: () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
      isActive: () => editor.isActive("heading", { level: 2 }),
    },
    {
      label: "Bullet List",
      icon: "•",
      action: () => editor.chain().focus().toggleBulletList().run(),
      isActive: () => editor.isActive("bulletList"),
    },
    {
      label: "Highlight",
      icon: "🖍",
      action: () => editor.chain().focus().toggleHighlight().run(),
      isActive: () => editor.isActive("highlight"),
    },
  ];

  const wordCount = editor.state.doc.textContent.split(/\s+/).filter(Boolean).length;

  return (
    <div className="flex items-center justify-between px-4 py-2 border-b border-glass-border">
      <div className="flex items-center gap-1">
        {buttons.map((btn) => (
          <button
            key={btn.label}
            onClick={btn.action}
            title={btn.label}
            className={clsx(
              "px-2 py-1 text-xs font-medium rounded transition-colors",
              btn.isActive()
                ? "bg-white/15 text-white"
                : "text-text-muted hover:text-text-secondary hover:bg-white/5",
            )}
          >
            {btn.icon}
          </button>
        ))}
      </div>
      <span className="text-xs text-text-muted">{wordCount} words</span>
    </div>
  );
}
