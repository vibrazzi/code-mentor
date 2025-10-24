FROM ollama/ollama:latest

ENV OLLAMA_MODEL=llama3.2:3b \
    OLLAMA_HOST=0.0.0.0 \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_FLASH_ATTENTION=false \
    OLLAMA_KEEP_ALIVE=10m

COPY deploy/ollama/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
