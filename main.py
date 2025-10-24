"""Aplicação FastAPI para o CodeMentor."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Literal

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware

APP_TITLE = "CodeMentor"
APP_DESCRIPTION = "Mentor de lógica de programação impulsionado por modelos Ollama."

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

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


app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION)
app.add_middleware(ForwardedProtoMiddleware)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def _get_ollama_url() -> str:
    """Determina a URL do Ollama baseada no ambiente."""
    env_url = os.getenv("OLLAMA_URL")
    if env_url:
        return env_url

    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "http://ollama:11434/api/generate"

    return "http://localhost:11434/api/generate"

OLLAMA_URL = _get_ollama_url()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

PROMPT_SISTEMA = """Você é o CodeMentor, um experiente mentor de lógica de programação.

Sua personalidade:
- Você é paciente, encorajador e didático
- Sempre explica conceitos de forma clara e progressiva
- Usa analogias do dia a dia quando possível
- Traz analogias simples que qualquer pessoa possa entender
- Dá exemplos práticos em Python
- Corrige erros gentilmente e explica o porquê
- Incentiva o aluno a pensar e resolver problemas
- Responde em português brasileiro
- Usa emojis para tornar as explicações mais amigáveis

Seu conhecimento:
- Variáveis, tipos de dados, operadores
- Estruturas de controle (if/else, loops)
- Funções, recursão, escopo
- Estruturas de dados (listas, dicionários, etc.)
- Algoritmos básicos e complexidade
- Boas práticas de programação
- Debugging e resolução de problemas

Quando responder:
1. Reconheça a pergunta ou problema
2. Explique o conceito teórico brevemente
3. Dê um exemplo prático em código
4. Incentive o aluno a praticar
5. Ofereça ajuda adicional se necessário

Mantenha as respostas concisas mas completas."""

MAX_HISTORY_TURNS = 3
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=1500)

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


def _call_ollama(prompt: str, max_retries: int = 2) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 150,
            "num_ctx": 1536,
            "num_thread": 6,
        },
    }

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=502,
                    detail=f"Ollama retornou status {response.status_code}: {error_detail}",
                )

            data = response.json()
            answer = data.get("response")
            if not answer:
                raise HTTPException(
                    status_code=502,
                    detail="Ollama não retornou conteúdo na resposta.",
                )

            return answer.strip()

        except requests.Timeout as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=504,
                detail=f"Timeout ao conectar com Ollama após {max_retries + 1} tentativas (limite: {REQUEST_TIMEOUT_SECONDS}s)",
            ) from exc

        except requests.ConnectionError as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Erro de conexão com Ollama: serviço pode estar iniciando. URL: {OLLAMA_URL}",
            ) from exc

        except requests.RequestException as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Erro ao conectar com Ollama: {exc}",
            ) from exc

        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="Resposta inválida do Ollama (JSON malformado).",
            ) from exc

    if last_exception:
        raise HTTPException(
            status_code=503,
            detail=f"Falha após {max_retries + 1} tentativas: {last_exception}",
        ) from last_exception

    raise HTTPException(status_code=500, detail="Erro desconhecido ao chamar Ollama")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve a interface web principal."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "OLLAMA_MODEL": OLLAMA_MODEL},
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
    """Endpoint para processar mensagens do chat."""
    prompt = _build_prompt(payload.history, payload.message)
    answer = _call_ollama(prompt)
    return ChatResponse(response=answer)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica conectividade com Ollama."""
    test_prompt = "Olá! Responda apenas com a palavra 'ok'."
    try:
        _ = _call_ollama(test_prompt)
    except HTTPException as exc:
        return {"status": "unhealthy", "detail": exc.detail}

    return {"status": "healthy", "ollama": OLLAMA_MODEL}


@app.get("/debug")
async def debug_info() -> dict:
    """Retorna informações de debug sobre a configuração."""
    return {
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "environment": {
            "OLLAMA_URL": os.getenv("OLLAMA_URL"),
            "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL"),
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
