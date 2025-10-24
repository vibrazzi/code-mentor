set -euo pipefail

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

echo ">> Ensuring model '${MODEL}' is available in Ollama cache."
if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "${MODEL}"; then
    echo ">> Model not found. Pulling '${MODEL}'..."
    ollama pull "${MODEL}"
    echo ">> Pull completed."
else
    echo ">> Model already present. Skipping pull."
fi

echo ">> Starting Ollama server..."
exec ollama serve
