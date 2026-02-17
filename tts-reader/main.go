package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/manifoldco/promptui"
)

var voices = []string{
	"alloy", "ash", "ballad", "coral", "echo",
	"fable", "nova", "onyx", "sage", "shimmer",
	"verse", "marin", "cedar",
}

func main() {
	filePath := flag.String("file", "", "path to file to convert (skips interactive picker)")
	voiceFlag := flag.String("voice", "", "TTS voice to use (skips voice prompt)")
	instrFlag := flag.String("instructions", "", "speech style instructions (skips prompt)")
	outDir := flag.String("output-dir", "audio_output", "output directory for audio files")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Usage: tts-reader [flags] [file]\n\n")
		fmt.Fprintf(os.Stderr, "Convert text files to speech using OpenAI TTS (gpt-4o-mini-tts).\n")
		fmt.Fprintf(os.Stderr, "Supports: .txt, .md, .docx, .pdf\n\n")
		fmt.Fprintf(os.Stderr, "If no file is specified, an interactive picker shows supported files\n")
		fmt.Fprintf(os.Stderr, "in the current directory.\n\n")
		fmt.Fprintf(os.Stderr, "Flags:\n")
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, "\nEnvironment:\n")
		fmt.Fprintf(os.Stderr, "  OPENAI_API_KEY    Required. Your OpenAI API key.\n")
		fmt.Fprintf(os.Stderr, "\nExamples:\n")
		fmt.Fprintf(os.Stderr, "  tts-reader                          # interactive mode\n")
		fmt.Fprintf(os.Stderr, "  tts-reader notes.md                 # convert specific file\n")
		fmt.Fprintf(os.Stderr, "  tts-reader --voice coral report.pdf  # skip voice prompt\n")
	}
	flag.Parse()

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fatal("OPENAI_API_KEY environment variable is not set.\nSet it with: export OPENAI_API_KEY=your-key-here")
	}

	file := resolveFile(*filePath, flag.Args())
	voice := resolveVoice(*voiceFlag)
	instructions := resolveInstructions(*instrFlag)

	fmt.Fprintf(os.Stderr, "Extracting text from %s...\n", filepath.Base(file))
	text, err := extractText(file)
	if err != nil {
		fatal("Failed to extract text: %v", err)
	}
	if strings.TrimSpace(text) == "" {
		fatal("No text content found in %s", file)
	}
	fmt.Fprintf(os.Stderr, "Extracted %d characters.\n", len(text))

	if err := os.MkdirAll(*outDir, 0755); err != nil {
		fatal("Failed to create output directory: %v", err)
	}
	baseName := strings.TrimSuffix(filepath.Base(file), filepath.Ext(file))
	outputPath := uniquePath(filepath.Join(*outDir, baseName+".mp3"))

	if err := convertToSpeech(apiKey, text, voice, instructions, outputPath); err != nil {
		fatal("Conversion failed: %v", err)
	}

	fmt.Fprintf(os.Stderr, "\nDone! Audio saved to: %s\n", outputPath)
}

func resolveFile(flagVal string, args []string) string {
	if flagVal != "" {
		return mustExist(flagVal)
	}
	if len(args) > 0 {
		return mustExist(args[0])
	}

	files := scanFiles(".")
	if len(files) == 0 {
		fatal("No supported files (.txt, .md, .docx, .pdf) found in current directory.")
	}

	prompt := promptui.Select{
		Label: "Select a file to convert",
		Items: files,
		Size:  15,
	}
	idx, _, err := prompt.Run()
	if err != nil {
		fatal("Selection cancelled.")
	}
	return files[idx]
}

func resolveVoice(flagVal string) string {
	if flagVal != "" {
		return flagVal
	}

	prompt := promptui.Select{
		Label: "Select a voice (marin and cedar recommended)",
		Items: voices,
		Size:  13,
	}
	_, result, err := prompt.Run()
	if err != nil {
		fatal("Selection cancelled.")
	}
	return result
}

func resolveInstructions(flagVal string) string {
	if flagVal != "" {
		return flagVal
	}

	prompt := promptui.Prompt{
		Label:   "Speech style instructions",
		Default: "Read naturally with clear enunciation.",
	}
	result, err := prompt.Run()
	if err != nil {
		fatal("Input cancelled.")
	}
	return result
}

func mustExist(path string) string {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		fatal("File not found: %s", path)
	}
	return path
}

func uniquePath(path string) string {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return path
	}
	ext := filepath.Ext(path)
	base := strings.TrimSuffix(path, ext)
	for i := 2; ; i++ {
		candidate := fmt.Sprintf("%s_%d%s", base, i, ext)
		if _, err := os.Stat(candidate); os.IsNotExist(err) {
			return candidate
		}
	}
}

func fatal(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "Error: "+format+"\n", args...)
	os.Exit(1)
}
