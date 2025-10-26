from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Dict, List, AsyncIterator

import httpx
from fastapi import HTTPException


def _env_float(name: str, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def _env_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def _get_ollama_url() -> str:
    env_url = os.getenv("OLLAMA_URL")
    if env_url:
        return env_url

    if os.getenv("RAILWAY_ENVIRONMENT"):
        return "http://ollama:11434/api/generate"

    return "http://localhost:11434/api/generate"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.7, minimum=0.0, maximum=2.0)
LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 800, minimum=50, maximum=2000)
LLM_TOP_P = _env_float("LLM_TOP_P", 0.9, minimum=0.0, maximum=1.0)

OLLAMA_URL = _get_ollama_url()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TEMPERATURE = _env_float("OLLAMA_TEMPERATURE", 0.7, minimum=0.0)
OLLAMA_TOP_P = _env_float("OLLAMA_TOP_P", 0.9, minimum=0.0, maximum=1.0)
OLLAMA_NUM_PREDICT = _env_int("OLLAMA_NUM_PREDICT", 512, minimum=32)
OLLAMA_NUM_CTX = _env_int("OLLAMA_NUM_CTX", 2048, minimum=256)
OLLAMA_NUM_THREAD = _env_int("OLLAMA_NUM_THREAD", 8, minimum=1)
OLLAMA_NUM_BATCH = _env_int("OLLAMA_NUM_BATCH", 512, minimum=1)

MAX_HISTORY_TURNS = 3
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))

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

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    """Context manager para obter o cliente HTTP."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        yield http_client
    finally:
        pass


async def startup():
    """Inicializa recursos na startup da aplicação."""
    global http_client
    http_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)


async def shutdown():
    """Libera recursos no shutdown da aplicação."""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None



async def call_groq(messages: List[Dict[str, str]], max_retries: int = 2, stream: bool = False) -> str | AsyncIterator[str]:
    """
    Chama a Groq API usando formato OpenAI-compatible.

    Args:
        messages: Lista de mensagens no formato OpenAI
        max_retries: Número de tentativas em caso de erro
        stream: Se True, retorna um async iterator de chunks

    Returns:
        Resposta completa (str) ou iterator de chunks (se stream=True)
    """
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="LLM_API_KEY não configurada. Adicione a chave da Groq no Railway."
        )

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "top_p": LLM_TOP_P,
        "stop": ["Aluno:"],
        "stream": stream,
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    if not http_client:
        raise HTTPException(status_code=500, detail="HTTP client não inicializado")

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            if stream:
                return _stream_groq_response(payload, headers)

            response = await http_client.post(
                LLM_API_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=502,
                    detail=f"Groq API retornou status {response.status_code}: {error_detail}",
                )

            data = response.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not answer:
                raise HTTPException(
                    status_code=502,
                    detail="Groq API não retornou conteúdo na resposta.",
                )

            return answer.strip()

        except httpx.TimeoutException as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=504,
                detail=f"Timeout ao conectar com Groq após {max_retries + 1} tentativas",
            ) from exc

        except httpx.RequestError as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Erro ao conectar com Groq: {exc}",
            ) from exc

        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="Resposta inválida da Groq API (JSON malformado).",
            ) from exc

    if last_exception:
        raise HTTPException(
            status_code=503,
            detail=f"Falha após {max_retries + 1} tentativas: {last_exception}",
        ) from last_exception

    raise HTTPException(status_code=500, detail="Erro desconhecido ao chamar Groq")


async def _stream_groq_response(payload: dict, headers: dict) -> AsyncIterator[str]:
    """Stream de resposta da Groq API."""
    if not http_client:
        raise HTTPException(status_code=500, detail="HTTP client não inicializado")

    async with http_client.stream(
        "POST",
        LLM_API_URL,
        json=payload,
        headers=headers,
        timeout=30,
    ) as response:
        if response.status_code != 200:
            error_detail = await response.aread()
            raise HTTPException(
                status_code=502,
                detail=f"Groq API retornou status {response.status_code}: {error_detail.decode()}",
            )

        async for line in response.aiter_lines():
            if not line or line.startswith(":"):
                continue

            if line.startswith("data: "):
                data_str = line[6:]

                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


async def call_ollama(prompt: str, max_retries: int = 2, stream: bool = False) -> str | AsyncIterator[str]:
    """
    Chama o Ollama local.

    Args:
        prompt: Prompt completo para o modelo
        max_retries: Número de tentativas em caso de erro
        stream: Se True, retorna um async iterator de chunks

    Returns:
        Resposta completa (str) ou iterator de chunks (se stream=True)
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "top_p": OLLAMA_TOP_P,
            "num_predict": OLLAMA_NUM_PREDICT,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_thread": OLLAMA_NUM_THREAD,
            "num_batch": OLLAMA_NUM_BATCH,
            "stop": ["\nAluno:", "\n\nAluno:", "Aluno:"],
        },
    }

    if not http_client:
        raise HTTPException(status_code=500, detail="HTTP client não inicializado")

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            if stream:
                return _stream_ollama_response(payload)

            response = await http_client.post(
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

        except httpx.TimeoutException as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=504,
                detail=f"Timeout ao conectar com Ollama após {max_retries + 1} tentativas (limite: {REQUEST_TIMEOUT_SECONDS}s)",
            ) from exc

        except httpx.ConnectError as exc:
            last_exception = exc
            if attempt < max_retries:
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Erro de conexão com Ollama: serviço pode estar iniciando. URL: {OLLAMA_URL}",
            ) from exc

        except httpx.RequestError as exc:
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


async def _stream_ollama_response(payload: dict) -> AsyncIterator[str]:
    """Stream de resposta do Ollama."""
    if not http_client:
        raise HTTPException(status_code=500, detail="HTTP client não inicializado")

    async with http_client.stream(
        "POST",
        OLLAMA_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as response:
        if response.status_code != 200:
            error_detail = await response.aread()
            raise HTTPException(
                status_code=502,
                detail=f"Ollama retornou status {response.status_code}: {error_detail.decode()}",
            )

        async for line in response.aiter_lines():
            if not line:
                continue

            try:
                data = json.loads(line)
                content = data.get("response", "")
                if content:
                    yield content

                if data.get("done", False):
                    break
            except json.JSONDecodeError:
                continue
