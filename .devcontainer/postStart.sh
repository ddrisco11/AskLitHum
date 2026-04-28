#!/usr/bin/env bash
# Runs on every Codespace start. Makes sure Ollama is up so app.py can reach it.
set -euo pipefail

if pgrep -x ollama >/dev/null 2>&1; then
  echo "[postStart] ollama already running"
else
  echo "[postStart] starting ollama serve..."
  nohup ollama serve >/tmp/ollama.log 2>&1 &
fi

# Brief wait so subsequent commands see a live daemon.
for i in {1..20}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "[postStart] ollama is up"
    break
  fi
  sleep 1
done

cat <<EOF

To run the app:
  python app.py                                   # API on :5001
  ( cd literary-oracle-main && npm run dev )      # UI  on :3000

EOF
