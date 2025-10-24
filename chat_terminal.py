"""
Script de chat interativo com CodeMentor via Ollama
"""

import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

def gerar_resposta_ollama(mensagem, historico=None):
    """Gera resposta usando Ollama com contexto de conversa"""

    if historico is None:
        historico = []

    prompt = f"""Você é o CodeMentor, um experiente mentor de lógica de programação.

Sua personalidade:
- Você é paciente, didático e encorajador
- Explica conceitos de forma clara e progressiva
- Usa analogias e exemplos práticos
- Incentiva o aprendizado ativo
- Mantém o foco em lógica de programação

Contexto da conversa anterior:
{chr(10).join([f"Usuário: {msg['user']}{chr(10)}CodeMentor: {msg['assistant']}" for msg in historico[-3:]])}

Usuário atual: {mensagem}

Responda como CodeMentor, focando em lógica de programação:"""

    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        "num_predict": 300
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=15)
        response.raise_for_status()

        data = response.json()
        resposta = data.get("response", "").strip()

        return resposta

    except requests.exceptions.RequestException as e:
        return f"❌ Erro ao conectar com Ollama: {e}"

def chat_interativo():
    """Interface de chat interativo no terminal"""

    print("🤖 CodeMentor - Seu mentor de lógica de programação")
    print("=" * 50)
    print("Digite suas perguntas sobre lógica de programação.")
    print("Digite 'sair' para encerrar o chat.")
    print()

    historico = []

    while True:
        try:
            mensagem = input("Você: ").strip()

            if not mensagem:
                continue

            if mensagem.lower() in ['sair', 'quit', 'exit']:
                print("👋 Até logo! Continue praticando lógica de programação!")
                break

            print("🤔 CodeMentor está pensando...")

            time.sleep(1)

            resposta = gerar_resposta_ollama(mensagem, historico)

            historico.append({"user": mensagem, "assistant": resposta})

            if len(historico) > 5:
                historico = historico[-5:]

            print(f"🤖 CodeMentor: {resposta}")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n👋 Chat encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")
            break

if __name__ == "__main__":
    chat_interativo()
