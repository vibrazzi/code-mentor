FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OLLAMA_URL=http://localhost:11434/api/generate \
    OLLAMA_MODEL=llama3.2:3b
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://ollama.ai/install.sh | sh
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . .
RUN ollama serve & \
    sleep 8 && \
    ollama pull "${OLLAMA_MODEL}" && \
    pkill -f ollama || true
EXPOSE 8000
CMD ["sh", "-c", "ollama serve & sleep 5 && uvicorn main:app --host 0.0.0.0 --port 8000"]
