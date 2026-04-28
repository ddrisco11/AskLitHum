#!/usr/bin/env bash
# One-shot setup: runs once when the Codespace is created.
set -euo pipefail

echo "[onCreate] installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "[onCreate] installing Python deps..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[onCreate] installing UI deps..."
( cd literary-oracle-main && npm install )

echo "[onCreate] building retrieval index if missing..."
if [ ! -f chunks.json ] || [ ! -f embeddings.npy ]; then
  python ingest.py
else
  echo "[onCreate] chunks.json + embeddings.npy already present, skipping ingest"
fi

echo "[onCreate] starting Ollama to pull the model..."
nohup ollama serve >/tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
# wait for the daemon to come up
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "[onCreate] pulling mistral:7b-instruct-q4_0 (~4 GB, slow)..."
ollama pull mistral:7b-instruct-q4_0

# Leave Ollama running for this session; postStart will (re)start it on subsequent boots.
echo "[onCreate] done."
