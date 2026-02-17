import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Highlight from "@tiptap/extension-highlight";
import { useEditorStore } from "@/stores/useEditorStore";
import { useUIStore } from "@/stores/useUIStore";
import { useEffect } from "react";
import { EditorToolbar } from "./EditorToolbar";

interface CanvasEditorProps {
  initialContent?: string;
}

export function CanvasEditor({ initialContent }: CanvasEditorProps) {
  const setContent = useEditorStore((s) => s.setContent);
  const setSelection = useEditorStore((s) => s.setSelection);
  const setSidebarContext = useUIStore((s) => s.setSidebarContext);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: "Paste or type your text here...",
      }),
      Highlight.configure({
        multicolor: true,
      }),
    ],
    content: initialContent || "",
    onUpdate: ({ editor: e }) => {
      setContent(e.getHTML());
    },
    onSelectionUpdate: ({ editor: e }) => {
      const { from, to } = e.state.selection;
      if (from !== to) {
        const text = e.state.doc.textBetween(from, to, " ");
        setSelection(text);
        setSidebarContext("voice");
      } else {
        setSelection("");
        setSidebarContext("settings");
      }
    },
    editorProps: {
      attributes: {
        class:
          "prose prose-invert prose-sm max-w-none min-h-[400px] outline-none px-6 py-4 text-text-primary leading-relaxed",
      },
    },
  });

  // Sync initial content
  useEffect(() => {
    if (editor && initialContent && !editor.getHTML().includes(initialContent.slice(0, 20))) {
      editor.commands.setContent(initialContent);
    }
  }, [editor, initialContent]);

  return (
    <div className="glass-panel-solid overflow-hidden animate-fade-in">
      {editor && <EditorToolbar editor={editor} />}
      <EditorContent editor={editor} />
    </div>
  );
}
