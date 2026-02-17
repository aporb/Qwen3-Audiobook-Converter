import { useCallback } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { CanvasEditor } from "@/components/editor/CanvasEditor";
import { EnhancedAudioPlayer } from "@/components/audio/EnhancedAudioPlayer";
import { KaraokeText } from "@/components/audio/KaraokeText";
import { VoiceSelector } from "@/components/tts/VoiceSelector";
import { PerformButton } from "@/components/tts/PerformButton";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { useEditorStore } from "@/stores/useEditorStore";
import { useTTSStore } from "@/stores/useTTSStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { useUIStore } from "@/stores/useUIStore";
import { useAudioStore } from "@/stores/useAudioStore";
import { usePreferencesStore } from "@/stores/usePreferencesStore";
import { useCleaningStore } from "@/stores/useCleaningStore";
import { TextProcessing } from "@/components/tts/TextProcessing";
import { useWebLLM } from "@/hooks/useWebLLM";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

export function StudioPage() {
  const content = useEditorStore((s) => s.content);
  const selection = useEditorStore((s) => s.selection);
  const engine = useEngineStore((s) => s.engine);
  const { isGenerating, progress, progressMessage, audioUrl, error, generateSpeech } =
    useTTSStore();
  const showIsland = useUIStore((s) => s.showIsland);
  const updateIsland = useUIStore((s) => s.updateIsland);
  const hideIsland = useUIStore((s) => s.hideIsland);
  const audioCurrentTime = useAudioStore((s) => s.currentTime);
  const audioDuration = useAudioStore((s) => s.duration);

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

  const aiCleaningEnabled = useCleaningStore((s) => s.aiCleaningEnabled);
  const cleanText = useCleaningStore((s) => s.cleanText);
  const cleaningInProgress = useCleaningStore((s) => s.isProcessing);

  const { generate: browserGenerate } = useWebLLM();

  // Use selected text or strip HTML from full content
  const textToSpeak = selection || content.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

  const handleSelectVoice = useCallback(
    (id: string | null, audioPath: string, rt: string) => {
      setSelectedVoiceId(id);
      setRefAudioPath(audioPath || null);
      setRefText(rt);
    },
    [setSelectedVoiceId, setRefAudioPath, setRefText],
  );

  const handlePerform = useCallback(async () => {
    if (!textToSpeak || isGenerating || cleaningInProgress) return;

    let finalText = textToSpeak;

    // AI cleaning step
    if (aiCleaningEnabled) {
      showIsland("Cleaning text with AI...");
      try {
        finalText = await cleanText(textToSpeak, browserGenerate);
      } catch {
        hideIsland();
        return;
      }
    }

    showIsland("Generating audio...");

    const unsub = useTTSStore.subscribe((state) => {
      if (state.isGenerating) {
        updateIsland(state.progress, state.progressMessage);
      } else {
        hideIsland();
        unsub();
      }
    });

    generateSpeech({
      text: finalText,
      engine,
      voice_mode: voiceMode,
      speaker,
      language,
      openai_voice: openaiVoice,
      openai_model: openaiModel,
      voice_description: voiceDescription || undefined,
      ref_audio: refAudioPath || undefined,
      ref_text: refText || undefined,
      fix_capitals: fixCapitals,
      remove_footnotes: removeFootnotes,
      normalize_chars: normalizeChars,
    });
  }, [textToSpeak, engine, voiceMode, speaker, language, openaiVoice, openaiModel, voiceDescription, refAudioPath, refText, fixCapitals, removeFootnotes, normalizeChars, isGenerating, cleaningInProgress, aiCleaningEnabled, cleanText, browserGenerate, generateSpeech, showIsland, updateIsland, hideIsland]);

  useKeyboardShortcuts([
    { key: "Enter", ctrl: true, action: handlePerform },
  ]);

  return (
    <div className="flex flex-col gap-5 h-full animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Studio</h1>
          <p className="text-sm text-text-secondary mt-1">
            {selection
              ? `Selected: ${selection.length} chars`
              : "Edit text, select passages, and generate audio."}
          </p>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0 overflow-y-auto" data-tour="studio-editor">
        <CanvasEditor />
      </div>

      {/* Voice Controls + Perform */}
      <GlassPanel solid>
        <div className="flex items-end gap-4">
          <div className="flex-1">
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
          </div>
          <div className="w-48">
            <PerformButton
              onClick={handlePerform}
              loading={isGenerating}
              disabled={!textToSpeak}
            />
          </div>
        </div>
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
          sampleText={textToSpeak}
        />
      </GlassPanel>

      {/* Progress */}
      {isGenerating && (
        <ProgressBar
          value={progress}
          label={progressMessage}
          variant={engine === "mlx" ? "local" : "cloud"}
        />
      )}

      {/* Error */}
      {error && (
        <GlassPanel solid className="border-red-500/30">
          <p className="text-sm text-red-400">{error}</p>
        </GlassPanel>
      )}

      {/* Audio + Karaoke */}
      {audioUrl && (
        <div className="flex flex-col gap-3">
          <EnhancedAudioPlayer url={audioUrl} />
          {textToSpeak && audioDuration > 0 && (
            <GlassPanel solid>
              <KaraokeText
                text={textToSpeak}
                currentTime={audioCurrentTime}
                duration={audioDuration}
              />
            </GlassPanel>
          )}
        </div>
      )}
    </div>
  );
}
