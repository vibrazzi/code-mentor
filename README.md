# CodeMentor · IA para Lógica de Programação

CodeMentor é um assistente especializado em lógica de programação, construído com FastAPI e alimentado por modelos hospedados no Ollama. O projeto foi pensado para portfólios profissionais: interface moderna, backend resiliente, testes automatizados e pipeline de deploy via Docker/Railway.

---

## Sumário
1. [Visão Geral](#visão-geral)
2. [Principais Recursos](#principais-recursos)
3. [Arquitetura](#arquitetura)
4. [Pré-requisitos](#pré-requisitos)
5. [Execução Local](#execução-local)
6. [Execução com Docker](#execução-com-docker)
7. [Deploy no Railway](#deploy-no-railway)
8. [Configuração por Ambiente](#configuração-por-ambiente)
9. [Testes e Qualidade](#testes-e-qualidade)
10. [Personalização](#personalização)
11. [Próximos Passos](#próximos-passos)
12. [Licença](#licença)

---

## Visão Geral

- **Objetivo:** oferecer mentoria de lógica de programação em português, com explicações graduais, exemplos em Python e analogias acessíveis.
- **Modelo base:** `llama3.2:3b` (ou qualquer modelo disponível no Ollama).
- **Stack principal:** FastAPI · Jinja2 · Vanilla JS · CSS customizado.

---

## Principais Recursos

- **Respostas estruturadas:** reconhecimento do problema, teoria resumida, exemplo em Python, convite à prática e oferta de apoio adicional.
- **Conversas com contexto:** histórico recente enviado ao modelo para manter coerência.
- **Interface responsiva:** layout futurista, sugestões rápidas, indicador de digitação e acessibilidade (ARIA/live regions).
- **Resiliência:** tratamento de erros da API do Ollama, health check dedicado e validação via Pydantic.
- **Pronto para produção:** Dockerfile otimizado, configuração Railway e suite de testes automatizados.

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

1. Empurre o repositório para o GitHub.
2. No Railway, crie um projeto usando **Deploy from GitHub repo** para o serviço FastAPI.
3. Crie um segundo serviço dedicado ao Ollama apontando para o Dockerfile `deploy/ollama/Dockerfile` deste repositório (o build já garante o download automático do modelo configurado).
4. O serviço utiliza o script `deploy/ollama/entrypoint.sh`, que baixa o modelo indicado em `OLLAMA_MODEL` na primeira inicialização e inicia o `ollama serve` automaticamente.
5. No serviço FastAPI, defina as variáveis de ambiente:
   - `OLLAMA_URL=http://<nome-do-servico-ollama>:11434/api/generate`
   - `OLLAMA_MODEL=llama3.2:3b`
   - `REQUEST_TIMEOUT_SECONDS=60` (opcional)
6. Dispare o deploy; o container FastAPI agora fica leve (apenas a aplicação). Para provedores externos (Hugging Face, Groq, OpenRouter), basta apontar `OLLAMA_URL` para o endpoint correspondente.

> **Dica:** se você quiser trocar o modelo padrão, ajuste `OLLAMA_MODEL` ao buildar a imagem (ou sobrescreva a variável no Railway). O entrypoint garante que o modelo seja baixado somente quando estiver ausente no volume persistente.

---

## Configuração por Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Endpoint da API do Ollama. |
| `OLLAMA_MODEL` | `llama3.2:3b` | Identificador do modelo a ser utilizado. |
| `REQUEST_TIMEOUT_SECONDS` | `120` | Timeout (segundos) das requisições ao Ollama. |
| `OLLAMA_TEMPERATURE` | `0.7` | Controle de criatividade; reduza para respostas mais objetivas. |
| `OLLAMA_TOP_P` | `0.9` | Nucleus sampling; menores valores geram respostas mais conservadoras. |
| `OLLAMA_NUM_PREDICT` | `256` | Limite de tokens gerados (quanto menor, mais rápido responde). |
| `OLLAMA_NUM_CTX` | `1536` | Tamanho do contexto enviado ao modelo (reduza para economizar memória). |
| `OLLAMA_NUM_THREAD` | `8` | Threads de inferência; ajuste conforme CPU disponível. |
| `OLLAMA_NUM_BATCH` | `512` | Tamanho do batch interno; diminua se houver gargalo de memória. |

Defina estas variáveis antes de iniciar o servidor (local ou produção). Exemplo:

```bash
export OLLAMA_MODEL="llama3.1:8b"
export OLLAMA_URL="http://ollama-service:11434/api/generate"
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
