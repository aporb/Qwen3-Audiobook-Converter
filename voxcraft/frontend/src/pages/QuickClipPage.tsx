import { useState, useCallback } from "react";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { ProgressBar } from "@/components/shared/ProgressBar";
import { VoiceSelector } from "@/components/tts/VoiceSelector";
import { PerformButton } from "@/components/tts/PerformButton";
import { TextProcessing } from "@/components/tts/TextProcessing";
import { EnhancedAudioPlayer } from "@/components/audio/EnhancedAudioPlayer";
import { KaraokeText } from "@/components/audio/KaraokeText";
import { useTTSStore } from "@/stores/useTTSStore";
import { useEngineStore } from "@/stores/useEngineStore";
import { useUIStore } from "@/stores/useUIStore";
import { useAudioStore } from "@/stores/useAudioStore";
import { usePreferencesStore } from "@/stores/usePreferencesStore";
import { useCleaningStore } from "@/stores/useCleaningStore";
import { useWebLLM } from "@/hooks/useWebLLM";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

export function QuickClipPage() {
  const [text, setText] = useState("");
  const [instruct, setInstruct] = useState("");
  const [openaiInstructions, setOpenaiInstructions] = useState("");

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

  const engine = useEngineStore((s) => s.engine);
  const { isGenerating, progress, progressMessage, audioUrl, error, generateSpeech } =
    useTTSStore();
  const showIsland = useUIStore((s) => s.showIsland);
  const updateIsland = useUIStore((s) => s.updateIsland);
  const hideIsland = useUIStore((s) => s.hideIsland);
  const audioCurrentTime = useAudioStore((s) => s.currentTime);
  const audioDuration = useAudioStore((s) => s.duration);

  const aiCleaningEnabled = useCleaningStore((s) => s.aiCleaningEnabled);
  const cleanText = useCleaningStore((s) => s.cleanText);
  const cleaningInProgress = useCleaningStore((s) => s.isProcessing);

  const { generate: browserGenerate } = useWebLLM();

  const handleSelectVoice = useCallback(
    (id: string | null, audioPath: string, rt: string) => {
      setSelectedVoiceId(id);
      setRefAudioPath(audioPath || null);
      setRefText(rt);
    },
    [setSelectedVoiceId, setRefAudioPath, setRefText],
  );

  const handlePerform = useCallback(async () => {
    if (!text.trim() || isGenerating || cleaningInProgress) return;

    let finalText = text;

    // AI cleaning step
    if (aiCleaningEnabled) {
      showIsland("Cleaning text with AI...");
      try {
        finalText = await cleanText(text, browserGenerate);
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
      instruct: instruct || undefined,
      openai_voice: openaiVoice,
      openai_model: openaiModel,
      openai_instructions: openaiInstructions || undefined,
      voice_description: voiceDescription || undefined,
      ref_audio: refAudioPath || undefined,
      ref_text: refText || undefined,
      fix_capitals: fixCapitals,
      remove_footnotes: removeFootnotes,
      normalize_chars: normalizeChars,
    });
  }, [text, engine, voiceMode, speaker, language, instruct, openaiVoice, openaiModel, openaiInstructions, voiceDescription, refAudioPath, refText, fixCapitals, removeFootnotes, normalizeChars, isGenerating, cleaningInProgress, aiCleaningEnabled, cleanText, browserGenerate, generateSpeech, showIsland, updateIsland, hideIsland]);

  useKeyboardShortcuts([
    { key: "Enter", ctrl: true, action: handlePerform },
  ]);

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-5 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Quick Clip</h1>
        <p className="text-sm text-text-secondary mt-1">
          Type or paste text, choose a voice, and hit Perform.
        </p>
      </div>

      {/* Text Input */}
      <GlassPanel solid>
        <textarea
          data-tour="quickclip-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to synthesize..."
          rows={6}
          className="w-full bg-transparent text-text-primary placeholder:text-text-muted resize-none outline-none text-sm leading-relaxed"
        />
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-glass-border">
          <span className="text-xs text-text-muted">
            {text.length.toLocaleString()} characters
          </span>
        </div>
      </GlassPanel>

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
        {/* Instruction field */}
        {engine === "mlx" && voiceMode === "custom_voice" && (
          <div className="mt-3">
            <label className="text-xs text-text-secondary font-medium">
              Style Instruction (optional)
            </label>
            <input
              type="text"
              value={instruct}
              onChange={(e) => setInstruct(e.target.value)}
              placeholder="e.g. Speak warmly and slowly"
              className="w-full mt-1 bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
          </div>
        )}
        {engine === "openai" && openaiModel === "gpt-4o-mini-tts" && (
          <div className="mt-3">
            <label className="text-xs text-text-secondary font-medium">
              Instructions (optional)
            </label>
            <input
              type="text"
              value={openaiInstructions}
              onChange={(e) => setOpenaiInstructions(e.target.value)}
              placeholder="e.g. Read in a calm, professional tone"
              className="w-full mt-1 bg-surface border border-glass-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted"
            />
          </div>
        )}
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
          sampleText={text}
        />
      </GlassPanel>

      {/* Generate */}
      <PerformButton
        onClick={handlePerform}
        loading={isGenerating}
        disabled={!text.trim()}
      />

      {/* Progress */}
      {isGenerating && (
        <div className="animate-slide-up">
          <ProgressBar
            value={progress}
            label={progressMessage}
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

      {/* Audio Player */}
      {audioUrl && (
        <div className="animate-slide-up flex flex-col gap-3">
          <EnhancedAudioPlayer url={audioUrl} />
          {text && audioDuration > 0 && (
            <GlassPanel solid>
              <KaraokeText
                text={text}
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
