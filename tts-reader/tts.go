package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

const (
	ttsEndpoint = "https://api.openai.com/v1/audio/speech"
	ttsModel    = "gpt-4o-mini-tts"
	maxChunkLen = 4096
)

type speechRequest struct {
	Model        string `json:"model"`
	Input        string `json:"input"`
	Voice        string `json:"voice"`
	Instructions string `json:"instructions,omitempty"`
	ResponseFmt  string `json:"response_format"`
}

func convertToSpeech(apiKey, text, voice, instructions, outputPath string) error {
	chunks := chunkText(text, maxChunkLen)
	fmt.Fprintf(os.Stderr, "Split into %d chunk(s).\n", len(chunks))

	outFile, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer outFile.Close()

	client := &http.Client{}
	for i, chunk := range chunks {
		fmt.Fprintf(os.Stderr, "\rConverting chunk %d/%d...", i+1, len(chunks))

		audio, err := requestSpeech(client, apiKey, chunk, voice, instructions)
		if err != nil {
			return fmt.Errorf("chunk %d/%d failed: %w", i+1, len(chunks), err)
		}
		if _, err := outFile.Write(audio); err != nil {
			return fmt.Errorf("failed to write chunk %d: %w", i+1, err)
		}
	}
	fmt.Fprintln(os.Stderr)
	return nil
}

func requestSpeech(client *http.Client, apiKey, text, voice, instructions string) ([]byte, error) {
	reqBody := speechRequest{
		Model:        ttsModel,
		Input:        text,
		Voice:        voice,
		Instructions: instructions,
		ResponseFmt:  "mp3",
	}
	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", ttsEndpoint, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("API request failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	return body, nil
}

func chunkText(text string, maxLen int) []string {
	text = strings.TrimSpace(text)
	if len(text) <= maxLen {
		return []string{text}
	}

	var chunks []string
	paragraphs := strings.Split(text, "\n")
	var current strings.Builder

	for _, para := range paragraphs {
		para = strings.TrimSpace(para)
		if para == "" {
			continue
		}

		if current.Len()+len(para)+1 > maxLen {
			if current.Len() > 0 {
				chunks = append(chunks, current.String())
				current.Reset()
			}
			if len(para) > maxLen {
				chunks = append(chunks, chunkBySentences(para, maxLen)...)
				continue
			}
		}
		if current.Len() > 0 {
			current.WriteString("\n")
		}
		current.WriteString(para)
	}

	if current.Len() > 0 {
		chunks = append(chunks, current.String())
	}

	return chunks
}

func chunkBySentences(text string, maxLen int) []string {
	sentences := splitSentences(text)
	var chunks []string
	var current strings.Builder

	for _, sentence := range sentences {
		sentence = strings.TrimSpace(sentence)
		if sentence == "" {
			continue
		}

		if current.Len()+len(sentence)+1 > maxLen {
			if current.Len() > 0 {
				chunks = append(chunks, current.String())
				current.Reset()
			}
			if len(sentence) > maxLen {
				chunks = append(chunks, chunkByWords(sentence, maxLen)...)
				continue
			}
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(sentence)
	}

	if current.Len() > 0 {
		chunks = append(chunks, current.String())
	}

	return chunks
}

func splitSentences(text string) []string {
	var sentences []string
	var current strings.Builder

	runes := []rune(text)
	for i := 0; i < len(runes); i++ {
		current.WriteRune(runes[i])
		if runes[i] == '.' || runes[i] == '!' || runes[i] == '?' {
			if i == len(runes)-1 || runes[i+1] == ' ' {
				sentences = append(sentences, current.String())
				current.Reset()
			}
		}
	}

	if current.Len() > 0 {
		sentences = append(sentences, current.String())
	}

	return sentences
}

func chunkByWords(text string, maxLen int) []string {
	words := strings.Fields(text)
	var chunks []string
	var current strings.Builder

	for _, word := range words {
		if current.Len()+len(word)+1 > maxLen {
			if current.Len() > 0 {
				chunks = append(chunks, current.String())
				current.Reset()
			}
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(word)
	}

	if current.Len() > 0 {
		chunks = append(chunks, current.String())
	}

	return chunks
}
