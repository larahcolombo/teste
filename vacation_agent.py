"""
FériasBot — Agente de chat especializado em férias e viagens.

Uso:
    python vacation_agent.py

Requer a variável de ambiente ANTHROPIC_API_KEY configurada.
"""

import anthropic
import os
import sys

SYSTEM_PROMPT = """Você é um agente especializado em férias e viagens, chamado **FériasBot**.

Seu papel é ajudar os usuários a planejar férias incríveis, respondendo perguntas sobre:

- **Destinos nacionais e internacionais**: praias, montanhas, cidades históricas, parques naturais
- **Planejamento de viagem**: melhor época para visitar, duração ideal, roteiros sugeridos
- **Hospedagem**: hotéis, pousadas, hostels, aluguel por temporada
- **Transporte**: voos, trens, ônibus, aluguel de carro
- **Orçamento**: estimativas de custo, dicas para economizar, viagens econômicas vs. luxo
- **Documentação**: passaportes, vistos, seguros viagem
- **Dicas culturais**: costumes locais, idiomas, gastronomia típica
- **Segurança**: regiões seguras, cuidados essenciais, vacinas necessárias
- **Atividades e atrações**: pontos turísticos, aventuras, ecoturismo, turismo cultural

Diretrizes:
- Responda **sempre em português brasileiro**
- Seja entusiasmado e inspire o usuário a viajar
- Dê recomendações concretas e práticas
- Quando pertinente, mencione prós e contras de cada opção
- Se não souber algo com certeza, diga claramente e sugira onde o usuário pode buscar mais informações
- Use emojis ocasionalmente para tornar a conversa mais animada ✈️🌴🗺️
"""


def print_separator():
    print("\n" + "─" * 60 + "\n")


def print_header():
    print("=" * 60)
    print("       ✈️  BEM-VINDO AO FÉRIAS BOT  🌴")
    print("   Seu assistente especializado em viagens e férias")
    print("=" * 60)
    print("\nDigite sua pergunta sobre férias e viagens.")
    print("Digite 'sair', 'exit' ou pressione Ctrl+C para encerrar.")
    print_separator()


def check_api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Erro: a variável de ambiente ANTHROPIC_API_KEY não está configurada.")
        print("\nConfigure-a antes de executar o script:")
        print("  export ANTHROPIC_API_KEY='sua-chave-aqui'")
        sys.exit(1)


def chat():
    check_api_key()

    client = anthropic.Anthropic()
    conversation_history = []

    print_header()

    while True:
        try:
            user_input = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAté a próxima viagem! ✈️ Boas férias! 🌴")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() in ("sair", "exit", "quit", "q"):
            print("\nAté a próxima viagem! ✈️ Boas férias! 🌴")
            break

        conversation_history.append({"role": "user", "content": user_input})

        print("\nFériasBot: ", end="", flush=True)

        try:
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=conversation_history,
                thinking={"type": "adaptive"},
            ) as stream:
                full_response = ""
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                    full_response += text
        except anthropic.APIConnectionError:
            print("\n[Erro de conexão. Verifique sua internet e tente novamente.]")
            conversation_history.pop()
            print_separator()
            continue
        except anthropic.RateLimitError:
            print("\n[Limite de requisições atingido. Aguarde um momento e tente novamente.]")
            conversation_history.pop()
            print_separator()
            continue
        except anthropic.APIStatusError as e:
            print(f"\n[Erro da API: {e.status_code}. Tente novamente.]")
            conversation_history.pop()
            print_separator()
            continue

        print()
        conversation_history.append({"role": "assistant", "content": full_response})
        print_separator()


if __name__ == "__main__":
    chat()
