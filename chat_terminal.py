"""
Script de chat interativo com CodeMentor via Ollama
"""

import asyncio
import time

from core import PROMPT_SISTEMA, call_ollama


async def gerar_resposta_ollama(mensagem, historico=None):
    """Gera resposta usando Ollama com contexto de conversa"""

    if historico is None:
        historico = []

    contexto = "\n".join([
        f"Usuário: {msg['user']}\nCodeMentor: {msg['assistant']}"
        for msg in historico[-3:]
    ])

    prompt = f"""{PROMPT_SISTEMA}

Contexto da conversa anterior:
{contexto}

Usuário atual: {mensagem}

Responda como CodeMentor, focando em lógica de programação:"""

    try:
        resposta = await call_ollama(prompt, stream=False)
        return resposta

    except Exception as e:
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

            resposta = asyncio.run(gerar_resposta_ollama(mensagem, historico))

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
