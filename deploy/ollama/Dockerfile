FROM ollama/ollama:latest

ENV OLLAMA_MODEL=llama3.2:3b \
    OLLAMA_HOST=0.0.0.0

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
