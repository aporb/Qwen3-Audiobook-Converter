import { useState, useCallback, useEffect } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { Modal } from "@/components/shared/Modal";
import { BookUploader } from "@/components/book/BookUploader";
import { BookMetadataCard } from "@/components/book/BookMetadataCard";
import { ChapterList } from "@/components/book/ChapterList";
import { CostEstimate } from "@/components/book/CostEstimate";
import { VoiceSelector } from "@/components/tts/VoiceSelector";
import { TextProcessing } from "@/components/tts/TextProcessing";
import { EnhancedAudioPlayer } from "@/components/audio/EnhancedAudioPlayer";
import { CastingDirector } from "@/components/casting/CastingDirector";
import { VoiceAssigner } from "@/components/casting/VoiceAssigner";
import { useProjectStore } from "@/stores/useProjectStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { useUIStore } from "@/stores/useUIStore";
import { usePreferencesStore } from "@/stores/usePreferencesStore";
import { useCleaningStore } from "@/stores/useCleaningStore";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { apiFetch, subscribeSSE } from "@/lib/api";

export function AudiobookPage() {
  const metadata = useProjectStore((s) => s.metadata);
  const bookId = useProjectStore((s) => s.bookId);
  const selectedChapters = useProjectStore((s) => s.selectedChapters);
  const clearBook = useProjectStore((s) => s.clearBook);
  const engine = useEngineStore((s) => s.engine);
  const showIsland = useUIStore((s) => s.showIsland);
  const updateIsland = useUIStore((s) => s.updateIsland);
  const hideIsland = useUIStore((s) => s.hideIsland);

  // Voice settings from preferences store
  const voiceMode = usePreferencesStore((s) => s.voiceMode);
  const setVoiceMode = usePreferencesStore((s) => s.setVoiceMode);
  const speaker = usePreferencesStore((s) => s.speaker);
  const setSpeaker = usePreferencesStore((s) => s.setSpeaker);
  const language = usePreferencesStore((s) => s.language);
  const setLanguage = usePreferencesStore((s) => s.setLanguage);
  const openaiVoice = usePreferencesStore((s) => s.openaiVoice);
  const setOpenaiVoice = usePreferencesStore((s) => s.setOpenaiVoice);
  const openaiModel = usePreferencesStore((s) => s.openaiModel);
  const setOpenaiModel = usePreferencesStore((s) => s.setOpenaiModel);
  const fixCapitals = usePreferencesStore((s) => s.fixCapitals);
  const setFixCapitals = usePreferencesStore((s) => s.setFixCapitals);
  const removeFootnotes = usePreferencesStore((s) => s.removeFootnotes);
  const setRemoveFootnotes = usePreferencesStore((s) => s.setRemoveFootnotes);
  const normalizeChars = usePreferencesStore((s) => s.normalizeChars);
  const setNormalizeChars = usePreferencesStore((s) => s.setNormalizeChars);

  // Voice Design / Clone
  const voiceDescription = usePreferencesStore((s) => s.voiceDescription);
  const setVoiceDescription = usePreferencesStore((s) => s.setVoiceDescription);
  const selectedVoiceId = usePreferencesStore((s) => s.selectedVoiceId);
  const setSelectedVoiceId = usePreferencesStore((s) => s.setSelectedVoiceId);
  const refAudioPath = usePreferencesStore((s) => s.refAudioPath);
  const setRefAudioPath = usePreferencesStore((s) => s.setRefAudioPath);
  const refText = usePreferencesStore((s) => s.refText);
  const setRefText = usePreferencesStore((s) => s.setRefText);

  // AI cleaning config
  const aiCleaningEnabled = useCleaningStore((s) => s.aiCleaningEnabled);
  const cleaningBackend = useCleaningStore((s) => s.cleaningBackend);
  const cleaningPreset = useCleaningStore((s) => s.cleaningPreset);
  const cleaningCustomPrompt = useCleaningStore((s) => s.customPrompt);
  const cleaningCustomBaseUrl = useCleaningStore((s) => s.customBaseUrl);
  const cleaningCustomModel = useCleaningStore((s) => s.customModel);
  const cleaningCustomApiKey = useCleaningStore((s) => s.customApiKey);

  // Conversion state
  const [isConverting, setIsConverting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMsg, setProgressMsg] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Modal state for "New Book" confirmation
  const [showNewBookModal, setShowNewBookModal] = useState(false);

  // Warn before navigating away during conversion
  useEffect(() => {
    if (!isConverting) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isConverting]);

  const handleSelectVoice = useCallback(
    (id: string | null, audioPath: string, rt: string) => {
      setSelectedVoiceId(id);
      setRefAudioPath(audioPath || null);
      setRefText(rt);
    },
    [setSelectedVoiceId, setRefAudioPath, setRefText],
  );

  const handleConvert = useCallback(async () => {
    if (!bookId || isConverting) return;
    setIsConverting(true);
    setProgress(0);
    setError(null);
    setAudioUrl(null);
    showIsland("Converting audiobook...");

    try {
      const { task_id } = await apiFetch<{ task_id: string }>(
        "/audiobook/convert",
        {
          method: "POST",
          body: JSON.stringify({
            book_id: bookId,
            engine,
            voice_mode: voiceMode,
            speaker,
            language,
            openai_voice: openaiVoice,
            openai_model: openaiModel,
            chapter_ids: selectedChapters,
            voice_description: voiceDescription || undefined,
            ref_audio: refAudioPath || undefined,
            ref_text: refText || undefined,
            fix_capitals: fixCapitals,
            remove_footnotes: removeFootnotes,
            normalize_chars: normalizeChars,
            ai_cleaning_enabled: aiCleaningEnabled && cleaningBackend !== "browser",
            cleaning_backend: cleaningBackend,
            cleaning_preset: cleaningPreset,
            cleaning_custom_prompt: cleaningPreset === "custom" ? cleaningCustomPrompt : undefined,
            cleaning_custom_base_url: cleaningBackend === "custom" ? cleaningCustomBaseUrl : undefined,
            cleaning_custom_model: cleaningBackend === "custom" ? cleaningCustomModel : undefined,
            cleaning_custom_api_key: cleaningBackend === "custom" ? cleaningCustomApiKey : undefined,
          }),
        },
      );

      subscribeSSE(
        `/audiobook/stream/${task_id}`,
        (evt) => {
          if (evt.event === "progress") {
            const frac = (evt.data.fraction as number) ?? 0;
            const msg = (evt.data.message as string) ?? "";
            setProgress(frac);
            setProgressMsg(msg);
            updateIsland(frac, msg);
          } else if (evt.event === "complete") {
            setIsConverting(false);
            setProgress(1);
            setAudioUrl(evt.data.audio_url as string);
            hideIsland();
          } else if (evt.event === "error") {
            setIsConverting(false);
            setError((evt.data.message as string) ?? "Conversion failed");
            hideIsland();
          }
        },
        () => {
          setIsConverting(false);
          hideIsland();
        },
      );
    } catch (e) {
      setIsConverting(false);
      setError((e as Error).message);
      hideIsland();
    }
  }, [bookId, engine, voiceMode, speaker, language, openaiVoice, openaiModel, voiceDescription, refAudioPath, refText, selectedChapters, fixCapitals, removeFootnotes, normalizeChars, aiCleaningEnabled, cleaningBackend, cleaningPreset, cleaningCustomPrompt, cleaningCustomBaseUrl, cleaningCustomModel, cleaningCustomApiKey, isConverting, showIsland, updateIsland, hideIsland]);

  useKeyboardShortcuts([
    { key: "Enter", ctrl: true, action: handleConvert },
  ]);

  const handleNewBook = () => {
    if (isConverting || audioUrl) {
      setShowNewBookModal(true);
    } else {
      clearBook();
    }
  };

  const confirmNewBook = () => {
    setShowNewBookModal(false);
    setAudioUrl(null);
    setError(null);
    clearBook();
  };

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Audiobook</h1>
          <p className="text-sm text-text-secondary mt-1">
            Import a book, select chapters, and convert to audio.
          </p>
        </div>
        {metadata && (
          <Button variant="ghost" size="sm" onClick={handleNewBook}>
            New Book
          </Button>
        )}
      </div>

      {/* Upload or metadata */}
      {!metadata ? (
        <BookUploader />
      ) : (
        <>
          <BookMetadataCard />
          <ChapterList />
          <CostEstimate />

          {/* Casting Director */}
          <CastingDirector />
          <VoiceAssigner />

          {/* Voice Settings */}
          <GlassPanel solid>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
              Voice Settings
            </h3>
            <VoiceSelector
              voiceMode={voiceMode}
              onVoiceModeChange={setVoiceMode}
              speaker={speaker}
              onSpeakerChange={setSpeaker}
              language={language}
              onLanguageChange={setLanguage}
              openaiVoice={openaiVoice}
              onOpenaiVoiceChange={setOpenaiVoice}
              openaiModel={openaiModel}
              onOpenaiModelChange={setOpenaiModel}
              voiceDescription={voiceDescription}
              onVoiceDescriptionChange={setVoiceDescription}
              selectedVoiceId={selectedVoiceId}
              onSelectVoice={handleSelectVoice}
            />
          </GlassPanel>

          {/* Text Processing */}
          <GlassPanel solid>
            <TextProcessing
              fixCapitals={fixCapitals}
              onFixCapitals={setFixCapitals}
              removeFootnotes={removeFootnotes}
              onRemoveFootnotes={setRemoveFootnotes}
              normalizeChars={normalizeChars}
              onNormalizeChars={setNormalizeChars}
              sampleText={metadata?.title}
            />
          </GlassPanel>

          {/* Convert Button */}
          <Button
            variant="primary"
            size="lg"
            loading={isConverting}
            disabled={selectedChapters.length === 0}
            onClick={handleConvert}
            className="w-full"
          >
            {isConverting ? "Converting..." : "Convert to Audiobook"}
          </Button>

          {/* Progress */}
          {isConverting && (
            <div className="animate-slide-up">
              <ProgressBar
                value={progress}
                label={progressMsg}
                variant={engine === "mlx" ? "local" : "cloud"}
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <GlassPanel solid className="border-red-500/30 animate-slide-up">
              <p className="text-sm text-red-400">{error}</p>
            </GlassPanel>
          )}

          {/* Result */}
          {audioUrl && (
            <div className="animate-slide-up">
              <EnhancedAudioPlayer url={audioUrl} downloadFormat="m4b" />
            </div>
          )}
        </>
      )}

      {/* New Book Confirmation Modal */}
      <Modal open={showNewBookModal} onClose={() => setShowNewBookModal(false)}>
        <h3 className="text-lg font-semibold text-text-primary mb-2">Start New Book?</h3>
        <p className="text-sm text-text-secondary mb-4">
          {isConverting
            ? "A conversion is in progress. Starting a new book will discard it."
            : "This will clear the current book and any generated audio."}
        </p>
        <div className="flex gap-3 justify-end">
          <Button variant="ghost" size="sm" onClick={() => setShowNewBookModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={confirmNewBook}>
            Continue
          </Button>
        </div>
      </Modal>
    </div>
  );
}
