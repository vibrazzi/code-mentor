#!/bin/sh
set -euo pipefail

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
BOOT_LOG="/tmp/ollama-bootstrap.log"

echo ">> Bootstrapping Ollama with model '${MODEL}'."
echo ">> Launching temporary Ollama daemon..."
OLLAMA_HOST=0.0.0.0 ollama serve >"${BOOT_LOG}" 2>&1 &
DAEMON_PID=$!

cleanup() {
    if kill -0 "${DAEMON_PID}" 2>/dev/null; then
        kill "${DAEMON_PID}" 2>/dev/null || true
        wait "${DAEMON_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo ">> Waiting Ollama daemon to accept connections..."
for _ in $(seq 1 30); do
    if OLLAMA_HOST=127.0.0.1 ollama list >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done

if [ "${READY:-0}" -ne 1 ]; then
    echo "!! Ollama daemon failed to start. Logs:"
    cat "${BOOT_LOG}" >&2
    exit 1
fi

if ! OLLAMA_HOST=127.0.0.1 ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "${MODEL}"; then
    echo ">> Model not found. Pulling '${MODEL}'..."
    OLLAMA_HOST=127.0.0.1 ollama pull "${MODEL}"
    echo ">> Pull completed."
else
    echo ">> Model already present. Skipping pull."
fi

cleanup
trap - EXIT

echo ">> Starting Ollama server..."
exec ollama serve
