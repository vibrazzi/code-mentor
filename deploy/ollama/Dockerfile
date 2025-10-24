FROM ollama/ollama:latest

ENV OLLAMA_MODEL=llama3.2:3b \
    OLLAMA_HOST=0.0.0.0

COPY deploy/ollama/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
