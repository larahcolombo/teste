import anthropic
import streamlit as st

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

st.set_page_config(
    page_title="FériasBot ✈️",
    page_icon="✈️",
    layout="centered",
)

st.title("✈️ FériasBot")
st.caption("Seu assistente especializado em viagens e férias 🌴")

with st.sidebar:
    st.header("⚙️ Configuração")
    api_key = st.text_input(
        "Chave da API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Obtenha sua chave em console.anthropic.com",
    )

    st.divider()
    st.markdown("**Sugestões de perguntas:**")
    suggestions = [
        "🏖️ Melhores praias do Brasil",
        "🗺️ Roteiro de 7 dias em Portugal",
        "💰 Como viajar barato pela Europa",
        "🗻 Destinos de montanha no inverno",
        "🌎 Preciso de visto para o Japão?",
        "🎭 Melhores cidades para o carnaval",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state.pending_suggestion = s

    st.divider()
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None

for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "✈️"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

if not st.session_state.messages:
    with st.chat_message("assistant", avatar="✈️"):
        st.markdown(
            "Olá! Sou o **FériasBot** 🌴 Estou aqui para ajudar você a planejar as "
            "férias dos seus sonhos! Me pergunta qualquer coisa sobre destinos, "
            "roteiros, hospedagem, orçamento e muito mais. Para onde você quer ir? ✈️"
        )

# Captura input: sugestão clicada ou digitado pelo usuário
user_input = None

if st.session_state.pending_suggestion:
    user_input = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None

typed = st.chat_input("Pergunte sobre destinos, roteiros, dicas de viagem...")
if typed:
    user_input = typed

if user_input:
    if not api_key:
        st.error("Configure sua chave da API Anthropic na barra lateral para começar.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="✈️"):
        placeholder = st.empty()
        full_response = ""

        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=st.session_state.messages,
                thinking={"type": "adaptive"},
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)

        except anthropic.AuthenticationError:
            st.error("Chave de API inválida. Verifique na barra lateral.")
            st.session_state.messages.pop()
            st.stop()
        except anthropic.APIConnectionError:
            st.error("Erro de conexão. Verifique sua internet e tente novamente.")
            st.session_state.messages.pop()
            st.stop()
        except anthropic.RateLimitError:
            st.error("Limite de requisições atingido. Aguarde um momento e tente novamente.")
            st.session_state.messages.pop()
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": full_response})
