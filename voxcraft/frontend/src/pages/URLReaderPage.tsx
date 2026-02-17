import { useCallback, useState } from "react";
import { EnhancedAudioPlayer } from "@/components/audio/EnhancedAudioPlayer";
import { VoiceSelector } from "@/components/tts/VoiceSelector";
import { ContentPreview } from "@/components/url/ContentPreview";
import { URLInput } from "@/components/url/URLInput";
import { Button } from "@/components/shared/Button";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { useAppStore } from "@/stores/useAppStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { usePreferencesStore } from "@/stores/usePreferencesStore";
import { useUIStore } from "@/stores/useUIStore";
import { ProcessingMode, useURLReaderStore } from "@/stores/useURLReaderStore";

export function URLReaderPage() {
  const [editedContent, setEditedContent] = useState<string | null>(null);
  const [instruct, setInstruct] = useState("");
  const [openaiInstructions, setOpenaiInstructions] = useState("");

  const {
    content,
    mode,
    isFetching,
    isConverting,
    progress,
    progressMessage,
    audioUrl,
    error,
    fetchContent,
    setMode,
    convertContent,
    reset,
    resetContent,
  } = useURLReaderStore();

  const engine = useEngineStore((s) => s.engine);
  const showIsland = useUIStore((s) => s.showIsland);
  const updateIsland = useUIStore((s) => s.updateIsland);
  const hideIsland = useUIStore((s) => s.hideIsland);

  const openaiApiKey = useAppStore((s) => s.openaiApiKey);

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
  const voiceDescription = usePreferencesStore((s) => s.voiceDescription);
  const setVoiceDescription = usePreferencesStore((s) => s.setVoiceDescription);
  const selectedVoiceId = usePreferencesStore((s) => s.selectedVoiceId);
  const setSelectedVoiceId = usePreferencesStore((s) => s.setSelectedVoiceId);
  const refAudioPath = usePreferencesStore((s) => s.refAudioPath);
  const setRefAudioPath = usePreferencesStore((s) => s.setRefAudioPath);
  const refText = usePreferencesStore((s) => s.refText);
  const setRefText = usePreferencesStore((s) => s.setRefText);

  const handleFetch = useCallback(async (inputUrl: string) => {
    setEditedContent(null);
    await fetchContent(inputUrl);
  }, [fetchContent]);

  const handleModeChange = useCallback((newMode: ProcessingMode) => {
    setMode(newMode);
  }, [setMode]);

  const handleEditContent = useCallback((newContent: string) => {
    setEditedContent(newContent);
  }, []);

  const handleSelectVoice = useCallback(
    (id: string | null, audioPath: string, rt: string) => {
      setSelectedVoiceId(id);
      setRefAudioPath(audioPath || null);
      setRefText(rt);
    },
    [setSelectedVoiceId, setRefAudioPath, setRefText],
  );

  const handleConvert = useCallback(async () => {
    if (!content || isConverting) return;

    showIsland("Converting URL to audio...");

    const unsub = useURLReaderStore.subscribe((state) => {
      if (state.isConverting) {
        updateIsland(state.progress, state.progressMessage || "Working...");
      } else {
        hideIsland();
        unsub();
      }
    });

    await convertContent({
      engine,
      voice_mode:
        voiceMode === "custom_voice" || voiceMode === "voice_clone" || voiceMode === "voice_design"
          ? voiceMode
          : "custom_voice",
      voice: speaker,
      language,
      instruct: instruct || undefined,
      ref_audio: refAudioPath || undefined,
      ref_text: refText || undefined,
      voice_description: voiceDescription || undefined,
      openai_model: openaiModel,
      openai_voice: openaiVoice,
      instructions: openaiInstructions || undefined,
      openai_api_key: openaiApiKey || undefined,
      content_override: editedContent || undefined,
    });
  }, [
    content,
    isConverting,
    showIsland,
    updateIsland,
    hideIsland,
    convertContent,
    engine,
    voiceMode,
    speaker,
    language,
    instruct,
    refAudioPath,
    refText,
    voiceDescription,
    openaiModel,
    openaiVoice,
    openaiInstructions,
    openaiApiKey,
    editedContent,
  ]);

  const handleReset = useCallback(() => {
    reset();
    setEditedContent(null);
    setInstruct("");
    setOpenaiInstructions("");
  }, [reset]);

  const handleNewURL = useCallback(() => {
    resetContent();
    setEditedContent(null);
  }, [resetContent]);

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">URL Reader</h1>
        <p className="text-sm text-text-secondary mt-1">
          Paste a link, choose Full Article or Summary + Insights, then generate audio.
        </p>
      </div>

      {!content && (
        <GlassPanel solid>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">
            Step 1: Enter URL
          </h3>
          <URLInput onSubmit={handleFetch} isLoading={isFetching} error={error} />
        </GlassPanel>
      )}

      {content && (
        <>
          <GlassPanel solid>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                Step 2: Content & Mode
              </h3>
              <button
                onClick={handleNewURL}
                className="text-sm text-text-secondary hover:text-text-primary"
              >
                New URL
              </button>
            </div>
            <ContentPreview
              content={content}
              onEdit={handleEditContent}
              onModeChange={handleModeChange}
              selectedMode={mode}
            />
          </GlassPanel>

          <GlassPanel solid>
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">
              Step 3: Voice Settings
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

            {engine === "mlx" && voiceMode === "custom_voice" && (
              <div className="mt-3">
                <label className="text-xs text-text-secondary font-medium">
                  Style Instruction (optional)
                </label>
                <input
                  type="text"
                  value={instruct}
                  onChange={(e) => setInstruct(e.target.value)}
                  placeholder="e.g. Speak clearly and naturally"
                  className="w-full mt-1 bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
                />
              </div>
            )}

            {engine === "openai" && openaiModel === "gpt-4o-mini-tts" && (
              <div className="mt-3">
                <label className="text-xs text-text-secondary font-medium">
                  OpenAI Instructions (optional)
                </label>
                <input
                  type="text"
                  value={openaiInstructions}
                  onChange={(e) => setOpenaiInstructions(e.target.value)}
                  placeholder="e.g. Read in a calm, insightful tone"
                  className="w-full mt-1 bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
                />
              </div>
            )}
          </GlassPanel>

          <div className="flex items-center justify-between">
            <div className="text-sm text-text-secondary">
              {mode === "full_article"
                ? `Full article (${content.word_count.toLocaleString()} words)`
                : "Summary + insights"}
            </div>
            <Button onClick={handleConvert} loading={isConverting} disabled={isConverting} size="lg">
              {isConverting ? "Converting..." : "Convert to Audio"}
            </Button>
          </div>
        </>
      )}

      {isConverting && (
        <div className="animate-slide-up">
          <ProgressBar
            value={progress}
            label={progressMessage}
            variant={engine === "mlx" ? "local" : "cloud"}
          />
        </div>
      )}

      {error && (
        <GlassPanel solid className="border-red-500/30 animate-slide-up">
          <p className="text-sm text-red-400">{error}</p>
        </GlassPanel>
      )}

      {audioUrl && (
        <div className="animate-slide-up flex flex-col gap-3">
          <GlassPanel solid>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-text-primary">Your Audio</h3>
              <Button variant="ghost" size="sm" onClick={handleReset}>
                Convert Another
              </Button>
            </div>
            <EnhancedAudioPlayer url={audioUrl} />
          </GlassPanel>
        </div>
      )}
    </div>
  );
}
