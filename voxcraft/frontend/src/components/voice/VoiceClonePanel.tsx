import { useState, useCallback, useRef, useEffect } from "react";
import { clsx } from "clsx";
import { Button } from "@/components/shared/Button";
import { AudioRecorder } from "./AudioRecorder";
import { useVoiceStore, type VoiceProfile } from "@/stores/useVoiceStore";

interface VoiceClonePanelProps {
  selectedVoiceId: string | null;
  onSelectVoice: (id: string | null, audioPath: string, refText: string) => void;
}

const ALLOWED_EXTENSIONS = [".wav", ".mp3", ".ogg", ".webm"];

export function VoiceClonePanel({ selectedVoiceId, onSelectVoice }: VoiceClonePanelProps) {
  const voices = useVoiceStore((s) => s.voices);
  const isLoading = useVoiceStore((s) => s.isLoading);
  const isUploading = useVoiceStore((s) => s.isUploading);
  const fetchVoices = useVoiceStore((s) => s.fetchVoices);
  const uploadVoice = useVoiceStore((s) => s.uploadVoice);
  const deleteVoice = useVoiceStore((s) => s.deleteVoice);

  const [dragOver, setDragOver] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadRefText, setUploadRefText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null);
  const [recordName, setRecordName] = useState("");
  const [recordRefText, setRecordRefText] = useState("");

  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchVoices();
  }, [fetchVoices]);

  const handleFileSelected = useCallback((file: File) => {
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
    if (!ALLOWED_EXTENSIONS.includes(ext)) return;
    setPendingFile(file);
    // Pre-fill name from filename (without extension)
    const baseName = file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ");
    setUploadName(baseName);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelected(file);
    },
    [handleFileSelected],
  );

  const handleUploadSave = useCallback(async () => {
    if (!pendingFile || !uploadName.trim()) return;
    try {
      const profile = await uploadVoice(pendingFile, uploadName.trim(), uploadRefText);
      onSelectVoice(profile.id, `/api/voices/audio/${profile.id}`, profile.ref_text);
      setPendingFile(null);
      setUploadName("");
      setUploadRefText("");
    } catch {
      // Error is set in the store
    }
  }, [pendingFile, uploadName, uploadRefText, uploadVoice, onSelectVoice]);

  const handleRecordingSave = useCallback(async () => {
    if (!recordingBlob || !recordName.trim()) return;
    try {
      const profile = await uploadVoice(recordingBlob, recordName.trim(), recordRefText);
      onSelectVoice(profile.id, `/api/voices/audio/${profile.id}`, profile.ref_text);
      setRecordingBlob(null);
      setRecordName("");
      setRecordRefText("");
    } catch {
      // Error is set in the store
    }
  }, [recordingBlob, recordName, recordRefText, uploadVoice, onSelectVoice]);

  const handleSelectSaved = useCallback(
    (voice: VoiceProfile) => {
      onSelectVoice(voice.id, `/api/voices/audio/${voice.id}`, voice.ref_text);
    },
    [onSelectVoice],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteVoice(id);
      if (selectedVoiceId === id) {
        onSelectVoice(null, "", "");
      }
      setDeleteConfirm(null);
    },
    [deleteVoice, selectedVoiceId, onSelectVoice],
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Saved Voices */}
      {voices.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
            Saved Voices
          </span>
          <div className="flex flex-col gap-1">
            {voices.map((v) => (
              <div
                key={v.id}
                className={clsx(
                  "flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all border",
                  selectedVoiceId === v.id
                    ? "bg-white/10 border-white/15"
                    : "hover:bg-white/5 border-transparent",
                )}
                onClick={() => handleSelectSaved(v)}
              >
                <div className="flex flex-col min-w-0">
                  <span className="text-sm text-text-primary truncate">{v.name}</span>
                  <span className="text-xs text-text-muted">
                    {new Date(v.created_at).toLocaleDateString()}
                  </span>
                </div>
                {deleteConfirm === v.id ? (
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(null)}>
                      Cancel
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-400" onClick={() => handleDelete(v.id)}>
                      Delete
                    </Button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirm(v.id);
                    }}
                    className="text-xs text-text-muted hover:text-red-400 transition-colors px-1"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {isLoading && <p className="text-xs text-text-muted">Loading voices...</p>}

      {/* Upload Reference Audio */}
      <div className="flex flex-col gap-2">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
          Upload Reference Audio
        </span>

        {!pendingFile ? (
          <div
            className={clsx(
              "border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors",
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
              accept=".wav,.mp3,.ogg,.webm"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelected(file);
              }}
            />
            <p className="text-sm text-text-secondary">
              Drop audio file here or click to browse
            </p>
            <p className="text-xs text-text-muted mt-1">WAV, MP3, OGG, or WebM</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2 p-3 border border-glass-border rounded-lg bg-surface">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-primary truncate">{pendingFile.name}</span>
              <button
                onClick={() => setPendingFile(null)}
                className="text-xs text-text-muted hover:text-text-secondary"
              >
                ×
              </button>
            </div>
            <input
              type="text"
              value={uploadName}
              onChange={(e) => setUploadName(e.target.value)}
              placeholder="Voice name"
              className="w-full bg-transparent border border-glass-border rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted"
            />
            <textarea
              value={uploadRefText}
              onChange={(e) => setUploadRefText(e.target.value)}
              placeholder="Transcript of reference audio (optional, improves quality)"
              rows={2}
              className="w-full bg-transparent border border-glass-border rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted resize-none"
            />
            <Button
              variant="primary"
              size="sm"
              loading={isUploading}
              disabled={!uploadName.trim()}
              onClick={handleUploadSave}
            >
              Save to Library
            </Button>
          </div>
        )}
      </div>

      {/* Record Reference Audio */}
      <div className="flex flex-col gap-2">
        <span className="text-xs text-text-muted font-medium uppercase tracking-wider">
          Record Reference Audio
        </span>

        {!recordingBlob ? (
          <AudioRecorder onRecorded={setRecordingBlob} />
        ) : (
          <div className="flex flex-col gap-2 p-3 border border-glass-border rounded-lg bg-surface">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-primary">Recorded audio</span>
              <button
                onClick={() => setRecordingBlob(null)}
                className="text-xs text-text-muted hover:text-text-secondary"
              >
                ×
              </button>
            </div>
            <input
              type="text"
              value={recordName}
              onChange={(e) => setRecordName(e.target.value)}
              placeholder="Voice name"
              className="w-full bg-transparent border border-glass-border rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted"
            />
            <textarea
              value={recordRefText}
              onChange={(e) => setRecordRefText(e.target.value)}
              placeholder="Transcript of what you said (optional, improves quality)"
              rows={2}
              className="w-full bg-transparent border border-glass-border rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted resize-none"
            />
            <Button
              variant="primary"
              size="sm"
              loading={isUploading}
              disabled={!recordName.trim()}
              onClick={handleRecordingSave}
            >
              Save to Library
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
