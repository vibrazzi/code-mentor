# CodeMentor · IA para Lógica de Programação

CodeMentor é um assistente especializado em lógica de programação, construído com FastAPI e alimentado por **Groq API** (llama-3.1-8b-instant) ou Ollama local. O projeto foi pensado para portfólios profissionais: interface moderna, backend resiliente, respostas ultra-rápidas (~300ms) e pipeline de deploy via Railway.

---

## Sumário

1. [Visão Geral](#visão-geral)
2. [Principais Recursos](#principais-recursos)
3. [Arquitetura](#arquitetura)
4. [Pré-requisitos](#pré-requisitos)
5. [Execução Local](#execução-local)
6. [Deploy no Railway](#deploy-no-railway)
7. [Configuração por Ambiente](#configuração-por-ambiente)
8. [Testes e Qualidade](#testes-e-qualidade)
9. [Personalização](#personalização)
10. [Próximos Passos](#próximos-passos)
11. [Licença](#licença)

---

## Visão Geral

- **Objetivo:** oferecer mentoria de lógica de programação em português, com explicações graduais, exemplos em Python e analogias acessíveis.
- **Modelo base:** `llama-3.1-8b-instant` via **Groq API** (padrão) ou `llama3.2:3b` via Ollama local.
- **Stack principal:** FastAPI · Groq API · Jinja2 · Vanilla JS · CSS customizado.
- **Performance:** Respostas em **~300-500ms** com Groq (vs 10-30s com Ollama local em CPU).

---

## Principais Recursos

- **⚡ Ultra-rápido:** Groq API com hardware dedicado entrega respostas em milissegundos
- **Respostas estruturadas:** reconhecimento do problema, teoria resumida, exemplo em Python, convite à prática
- **Conversas com contexto:** histórico recente para manter coerência
- **Interface responsiva:** layout futurista, sugestões rápidas, indicador de digitação e acessibilidade (ARIA)
- **Dual provider:** suporta Groq API (recomendado) ou Ollama local como fallback
- **Resiliência:** retry logic, tratamento de erros e validação via Pydantic
- **Pronto para produção:** Deploy no Railway em minutos

---

## Arquitetura

```
code-mentor/
├── main.py                # Aplicação FastAPI e integração com Ollama
├── static/
│   ├── css/styles.css     # Tema futurista responsivo
│   └── js/app.js          # UX do chat (histórico, feedback visual, fetch API)
├── templates/index.html   # Template Jinja2 da interface
├── chat_terminal.py       # CLI para conversas rápidas (debug)
├── tests/test_app.py      # Testes unitários
├── Dockerfile             # Build completo com Ollama + aplicação
├── requirements.txt       # Dependências Python
├── railway.json           # Comando de start para deploy no Railway
└── README.md
```

> **Nota:** mantenha o Ollama rodando em um serviço dedicado no ambiente de produção. Executar modelo e API no mesmo container exige recursos elevados.

---

## Pré-requisitos

- Python **3.12** ou superior
- [Ollama](https://ollama.com) instalado e operando (`ollama serve`)
- Modelo baixado localmente (`ollama pull llama3.2:3b`) ou endpoint remoto compatível
- Docker (opcional) para build e deploy containerizado

---

## Execução Local

```bash
git clone https://github.com/seu-usuario/code-mentor.git
cd code-mentor

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
ollama pull llama3.2:3b     # execute apenas na primeira vez

uvicorn main:app --reload
```

Abra `http://127.0.0.1:8000` para iniciar a sessão com o mentor.

---

## Execução com Docker

```bash
docker build -t codementor .
docker run --rm \
  -e OLLAMA_URL=http://host.docker.internal:11434/api/generate \
  -e OLLAMA_MODEL=llama3.2:3b \
  -p 8000:8000 codementor
```

> O container não inclui o Ollama. Execute `ollama serve` e `ollama pull <modelo>` no host e exponha a porta 11434. Em macOS/Windows use `host.docker.internal`; em Linux utilize o IP da máquina anfitriã ou uma rede Docker customizada.

---

## Deploy no Railway

### ⚡ Opção 1: Com Groq API (Recomendado - Ultra Rápido)

1. **Obtenha uma API Key da Groq:**

   - Acesse: https://console.groq.com/
   - Faça login e crie uma API Key gratuita
   - Copie a chave (começa com `gsk_...`)

2. **Deploy no Railway:**

   - Empurre o repositório para o GitHub
   - No Railway, crie um projeto usando **Deploy from GitHub repo**
   - Adicione as variáveis de ambiente:
     ```
     LLM_PROVIDER=groq
     LLM_API_KEY=gsk_sua_chave_aqui
     LLM_MODEL=llama-3.1-8b-instant
     LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
     LLM_MAX_TOKENS=800
     ```

3. **Pronto!** ✨
   - Deploy automático em 1-2 minutos
   - Respostas em ~300-500ms
   - Plano gratuito: 14,400 requests/dia
   - Custo zero de infraestrutura

### 🔧 Opção 2: Com Ollama Local (Fallback)

1. Crie dois serviços no Railway:

   - **Serviço 1:** FastAPI (este repositório)
   - **Serviço 2:** Ollama dedicado (usando `deploy/ollama/Dockerfile`)

2. Configure as variáveis no serviço FastAPI:

   ```
   LLM_PROVIDER=ollama
   OLLAMA_URL=http://<nome-do-servico-ollama>:11434/api/generate
   OLLAMA_MODEL=llama3.2:3b
   ```

3. O Ollama usa o script `deploy/ollama/entrypoint.sh` que:
   - Baixa o modelo automaticamente na primeira inicialização
   - Usa volume persistente para armazenar o modelo
   - Inicia o `ollama serve` automaticamente

> **Nota:** Ollama em CPU no Railway é ~60-100x mais lento que Groq (~15-30s vs 0.3-0.5s)

---

## Configuração por Ambiente

### Variáveis Groq API (Recomendado)

| Variável          | Padrão                                            | Descrição                                                                              |
| ----------------- | ------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `LLM_PROVIDER`    | `ollama`                                          | Provider: `groq` (recomendado) ou `ollama`                                             |
| `LLM_API_KEY`     | -                                                 | **Obrigatório para Groq** - API Key da Groq Console                                    |
| `LLM_API_URL`     | `https://api.groq.com/openai/v1/chat/completions` | Endpoint da Groq API                                                                   |
| `LLM_MODEL`       | `llama-3.1-8b-instant`                            | Modelo Groq: `llama-3.1-8b-instant`, `llama-3.1-70b-versatile` ou `mixtral-8x7b-32768` |
| `LLM_MAX_TOKENS`  | `800`                                             | Limite de tokens por resposta (50-2000)                                                |
| `LLM_TEMPERATURE` | `0.7`                                             | Criatividade: 0.0 (conservador) - 2.0 (criativo)                                       |
| `LLM_TOP_P`       | `0.9`                                             | Nucleus sampling (0.0-1.0)                                                             |

### Variáveis Ollama Local (Fallback)

| Variável             | Padrão                                | Descrição                               |
| -------------------- | ------------------------------------- | --------------------------------------- |
| `OLLAMA_URL`         | `http://localhost:11434/api/generate` | Endpoint da API do Ollama               |
| `OLLAMA_MODEL`       | `llama3.2:3b`                         | Identificador do modelo                 |
| `OLLAMA_NUM_PREDICT` | `150`                                 | Limite de tokens gerados                |
| `OLLAMA_NUM_CTX`     | `512`                                 | Tamanho do contexto                     |
| `OLLAMA_NUM_THREAD`  | `8`                                   | Threads de inferência (ajuste para CPU) |
| `OLLAMA_NUM_BATCH`   | `512`                                 | Batch size interno                      |
| `OLLAMA_TEMPERATURE` | `0.7`                                 | Controle de criatividade                |
| `OLLAMA_TOP_P`       | `0.9`                                 | Nucleus sampling                        |

### Variáveis Gerais

| Variável                  | Padrão | Descrição                          |
| ------------------------- | ------ | ---------------------------------- |
| `REQUEST_TIMEOUT_SECONDS` | `60`   | Timeout das requisições (segundos) |

**Exemplo Groq:**

```bash
export LLM_PROVIDER="groq"
export LLM_API_KEY="gsk_..."
export LLM_MODEL="llama-3.1-8b-instant"
uvicorn main:app
```

**Exemplo Ollama:**

```bash
export LLM_PROVIDER="ollama"
export OLLAMA_URL="http://localhost:11434/api/generate"
uvicorn main:app
```

---

## Testes e Qualidade

```bash
source .venv/bin/activate
python -m unittest discover -s tests
```

Os testes atuais validam:

- Renderização da homepage
- Fluxo feliz do endpoint `/api/chat` (mockando o Ollama)
- Regras de validação (payload vazio → HTTP 422)

Inclua testes adicionais conforme evoluir o projeto (por exemplo, testes end-to-end com Playwright).

---

## Personalização

- **Prompt e tom:** ajuste a constante `PROMPT_SISTEMA` em `main.py`.
- **Layout e identidade visual:** edite `static/css/styles.css` ou substitua o template `templates/index.html`.
- **Comportamento do chat:** altere `static/js/app.js` para mudar regras de histórico, animações e UX.
- **Integração com outros modelos:** atualize `OLLAMA_MODEL` ou adapte `_call_ollama` para consumir APIs externas.

---

## Próximos Passos

- [ ] Implementar autenticação para acompanhar histórico individual.
- [ ] Adicionar métricas de uso e logs estruturados.
- [ ] Criar testes end-to-end para a camada de frontend.
- [ ] Disponibilizar integrações com outros idiomas.

---

## Licença

Projeto de portfólio. Utilize como base educacional ou ponto de partida profissional. Ao compartilhar melhorias, cite a autoria original.
