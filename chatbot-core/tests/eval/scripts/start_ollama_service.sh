#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <results-dir>" >&2
  exit 1
fi

RESULTS_DIR="$1"
OLLAMA_LOG="$RESULTS_DIR/ollama-server.log"

nohup ollama serve > "$OLLAMA_LOG" 2>&1 &
sleep 5

for attempt in {1..30}; do
  if curl -fsS http://127.0.0.1:11434/api/tags > /dev/null 2>&1 || \
    curl -fsS http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is ready."
    exit 0
  fi

  echo "Attempt $attempt: Ollama is not ready yet."
  sleep 2
done

echo "Ollama did not become ready within 60 seconds." >&2
echo "=== Ollama Server Log ===" >&2
cat "$OLLAMA_LOG" >&2
exit 1
