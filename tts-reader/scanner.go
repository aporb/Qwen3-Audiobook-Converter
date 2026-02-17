package main

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

var supportedExtensions = map[string]bool{
	".txt":  true,
	".md":   true,
	".docx": true,
	".pdf":  true,
}

func scanFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}

	var files []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		ext := strings.ToLower(filepath.Ext(entry.Name()))
		if supportedExtensions[ext] {
			files = append(files, entry.Name())
		}
	}
	sort.Strings(files)
	return files
}
