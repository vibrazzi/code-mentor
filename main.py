from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Dict, Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware

import core
from core import (
    PROMPT_SISTEMA,
    MAX_HISTORY_TURNS,
    LLM_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_URL,
    LLM_API_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TOP_P,
    LLM_API_KEY,
    OLLAMA_TEMPERATURE,
    OLLAMA_TOP_P,
    OLLAMA_NUM_PREDICT,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_THREAD,
    OLLAMA_NUM_BATCH,
    REQUEST_TIMEOUT_SECONDS,
    call_groq,
    call_ollama,
)

APP_TITLE = "CodeMentor"
APP_DESCRIPTION = "Mentor de lógica de programação com IA (Groq/Ollama)."

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (startup/shutdown)."""
    await core.startup()
    yield
    await core.shutdown()


class ForwardedProtoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        proto = request.headers.get("x-forwarded-proto")
        if proto:
            request.scope["scheme"] = proto

        host = request.headers.get("x-forwarded-host")
        if host:
            if ":" in host:
                host_name, port = host.rsplit(":", 1)
                try:
                    request.scope["server"] = (host_name, int(port))
                except ValueError:
                    request.scope["server"] = (host, request.scope["server"][1])
            else:
                request.scope["server"] = (host, request.scope["server"][1])

        return await call_next(request)


app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, lifespan=lifespan)
app.add_middleware(ForwardedProtoMiddleware)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=3000)

    @validator("content")
    def _strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Conteúdo vazio não é permitido.")
        return cleaned


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    history: List[ConversationTurn] = Field(default_factory=list)

    @validator("message")
    def _strip_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Mensagem vazia não é permitida.")
        return cleaned


class ChatResponse(BaseModel):
    response: str


def _build_prompt(history: List[ConversationTurn], message: str) -> str:
    prompt_parts = [PROMPT_SISTEMA, ""]

    recent_history = history[-MAX_HISTORY_TURNS * 2 :]
    for item in recent_history:
        if item.role == "user":
            prompt_parts.append(f"Aluno: {item.content}")
        else:
            prompt_parts.append(f"CodeMentor: {item.content}")

    prompt_parts.append(f"Aluno: {message}")
    prompt_parts.append("CodeMentor:")
    return "\n".join(prompt_parts)


def _build_messages(history: List[ConversationTurn], message: str) -> List[Dict[str, str]]:
    """Constrói formato de mensagens OpenAI-compatible para Groq."""
    messages = [{"role": "system", "content": PROMPT_SISTEMA}]

    recent_history = history[-MAX_HISTORY_TURNS * 2 :]
    for item in recent_history:
        messages.append({"role": item.role, "content": item.content})

    messages.append({"role": "user", "content": message})
    return messages


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve a interface web principal."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "OLLAMA_MODEL": OLLAMA_MODEL},
    )


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest) -> StreamingResponse:
    """Endpoint para processar mensagens do chat com streaming."""

    async def generate_stream() -> AsyncIterator[str]:
        """Gerador assíncrono para streaming de resposta."""
        try:
            if LLM_PROVIDER == "groq":
                messages = _build_messages(payload.history, payload.message)
                stream = await call_groq(messages, stream=True)
            else:
                prompt = _build_prompt(payload.history, payload.message)
                stream = await call_ollama(prompt, stream=True)

            async for chunk in stream:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            yield "data: [DONE]\n\n"

        except HTTPException as exc:
            error_data = json.dumps({"error": exc.detail, "status_code": exc.status_code})
            yield f"data: {error_data}\n\n"
        except Exception as exc:
            error_data = json.dumps({"error": str(exc), "status_code": 500})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica conectividade com Ollama."""
    test_prompt = "Olá! Responda apenas com a palavra 'ok'."
    try:
        _ = await call_ollama(test_prompt)
    except HTTPException as exc:
        return {"status": "unhealthy", "detail": exc.detail}

    return {"status": "healthy", "ollama": OLLAMA_MODEL}


@app.get("/debug")
async def debug_info() -> Dict[str, Any]:
    """Retorna informações de debug sobre a configuração."""
    base_info = {
        "provider": LLM_PROVIDER,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
    }

    if LLM_PROVIDER == "groq":
        base_info.update({
            "api_url": LLM_API_URL,
            "model": LLM_MODEL,
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
            "top_p": LLM_TOP_P,
            "api_key_configured": bool(LLM_API_KEY),
        })
    else:
        base_info.update({
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL,
            "temperature": OLLAMA_TEMPERATURE,
            "top_p": OLLAMA_TOP_P,
            "num_predict": OLLAMA_NUM_PREDICT,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_thread": OLLAMA_NUM_THREAD,
            "num_batch": OLLAMA_NUM_BATCH,
        })

    return base_info


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
