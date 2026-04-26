"""
AgendaBot Web — Interface Streamlit para o agente de agendamento.

Uso:
    streamlit run scheduling_agent_web.py
"""

import anthropic
import json
import streamlit as st
from datetime import datetime

TODAY = datetime.now().strftime("%Y-%m-%d")

# --- Calendários simulados ---
HUSBAND_CALENDAR: dict[str, list[dict]] = {
    "2026-04-27": [
        {"start": "09:00", "end": "10:00", "title": "Reunião de equipe"},
        {"start": "14:00", "end": "15:30", "title": "Dentista"},
    ],
    "2026-04-28": [
        {"start": "10:00", "end": "12:00", "title": "Almoço com cliente"},
        {"start": "16:00", "end": "17:00", "title": "Academia"},
    ],
    "2026-04-29": [],
    "2026-04-30": [
        {"start": "08:00", "end": "09:00", "title": "Conferência online"},
    ],
    "2026-05-02": [
        {"start": "09:00", "end": "18:00", "title": "Viagem de trabalho"},
    ],
    "2026-05-03": [
        {"start": "09:00", "end": "18:00", "title": "Viagem de trabalho"},
    ],
    "2026-05-05": [
        {"start": "10:00", "end": "11:00", "title": "Reunião de projeto"},
    ],
}

MY_CALENDAR: dict[str, list[dict]] = {
    "2026-04-27": [
        {"start": "11:00", "end": "12:00", "title": "Reunião com RH"},
    ],
    "2026-04-29": [
        {"start": "09:00", "end": "10:00", "title": "Médico"},
    ],
    "2026-05-05": [
        {"start": "14:00", "end": "15:00", "title": "Apresentação trimestral"},
    ],
}


# --- Funções de calendário (usam st.session_state para eventos criados) ---

def _time_to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _find_conflicts(start: str, end: str, events: list[dict]) -> list[dict]:
    req_start = _time_to_minutes(start)
    req_end = _time_to_minutes(end)
    return [
        e for e in events
        if req_start < _time_to_minutes(e["end"]) and req_end > _time_to_minutes(e["start"])
    ]


def check_husband_availability(date: str, start_time: str, end_time: str) -> dict:
    events = HUSBAND_CALENDAR.get(date, [])
    conflicts = _find_conflicts(start_time, end_time, events)
    if conflicts:
        return {
            "available": False,
            "conflicts": conflicts,
            "message": (
                f"Marido indisponível em {date} das {start_time}–{end_time}. "
                "Conflito(s): "
                + ", ".join(f"'{c['title']}' ({c['start']}–{c['end']})" for c in conflicts)
            ),
        }
    return {
        "available": True,
        "message": f"Marido disponível em {date} das {start_time}–{end_time}.",
    }


def get_husband_schedule(date: str) -> dict:
    events = HUSBAND_CALENDAR.get(date, [])
    if not events:
        return {"date": date, "events": [], "message": f"Marido sem compromissos em {date}."}
    summary = ", ".join(f"'{e['title']}' ({e['start']}–{e['end']})" for e in events)
    return {"date": date, "events": events, "message": f"Agenda do marido em {date}: {summary}."}


def get_my_schedule(date: str) -> dict:
    base = MY_CALENDAR.get(date, [])
    agent_events = [e for e in st.session_state.scheduled_events if e["date"] == date]
    all_events = base + agent_events
    if not all_events:
        return {"date": date, "events": [], "message": f"Você não tem compromissos em {date}."}
    summary = ", ".join(f"'{e['title']}' ({e['start']}–{e['end']})" for e in all_events)
    return {"date": date, "events": all_events, "message": f"Sua agenda em {date}: {summary}."}


def create_event(
    date: str,
    start_time: str,
    end_time: str,
    title: str,
    description: str = "",
    include_husband: bool = True,
) -> dict:
    if include_husband:
        avail = check_husband_availability(date, start_time, end_time)
        if not avail["available"]:
            return {
                "success": False,
                "message": f"Evento não criado — marido indisponível. {avail['message']}",
            }

    event = {
        "id": len(st.session_state.scheduled_events) + 1,
        "date": date,
        "start": start_time,
        "end": end_time,
        "title": title,
        "description": description,
        "attendees": ["você"] + (["marido"] if include_husband else []),
    }
    st.session_state.scheduled_events.append(event)
    attendees = " e ".join(event["attendees"])
    return {
        "success": True,
        "event": event,
        "message": f"Evento '{title}' criado em {date} das {start_time}–{end_time} com convite para: {attendees}.",
    }


def suggest_alternative_slots(date: str, duration_minutes: int) -> dict:
    husband_events = HUSBAND_CALENDAR.get(date, [])
    my_events = MY_CALENDAR.get(date, []) + [
        e for e in st.session_state.scheduled_events if e["date"] == date
    ]

    busy = sorted(
        (_time_to_minutes(e["start"]), _time_to_minutes(e["end"]))
        for e in husband_events + my_events
    )

    slots: list[dict] = []
    cursor = 8 * 60
    day_end = 20 * 60

    while cursor + duration_minutes <= day_end and len(slots) < 5:
        slot_end = cursor + duration_minutes
        if not any(cursor < be and slot_end > bs for bs, be in busy):
            slots.append({
                "start": f"{cursor // 60:02d}:{cursor % 60:02d}",
                "end": f"{slot_end // 60:02d}:{slot_end % 60:02d}",
            })
        cursor += 30

    if not slots:
        return {"date": date, "slots": [], "message": f"Nenhum horário disponível para os dois em {date}."}
    slots_str = ", ".join(f"{s['start']}–{s['end']}" for s in slots)
    return {
        "date": date,
        "slots": slots,
        "message": f"Horários disponíveis para os dois em {date}: {slots_str}.",
    }


TOOLS: list[dict] = [
    {
        "name": "check_husband_availability",
        "description": (
            "Verifica se o marido está disponível em um horário específico. "
            "Chame ANTES de criar qualquer evento que inclua o marido."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
                "start_time": {"type": "string", "description": "Hora de início no formato HH:MM"},
                "end_time": {"type": "string", "description": "Hora de término no formato HH:MM"},
            },
            "required": ["date", "start_time", "end_time"],
        },
    },
    {
        "name": "get_husband_schedule",
        "description": "Retorna todos os compromissos do marido em uma data específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_my_schedule",
        "description": "Retorna todos os meus compromissos em uma data específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "create_event",
        "description": (
            "Cria um novo evento no calendário e envia convite. "
            "Quando include_husband=true, valida automaticamente a disponibilidade do marido antes de criar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
                "start_time": {"type": "string", "description": "Hora de início no formato HH:MM"},
                "end_time": {"type": "string", "description": "Hora de término no formato HH:MM"},
                "title": {"type": "string", "description": "Título do evento"},
                "description": {"type": "string", "description": "Descrição opcional do evento"},
                "include_husband": {
                    "type": "boolean",
                    "description": "Se true, inclui o marido no convite e valida sua disponibilidade",
                },
            },
            "required": ["date", "start_time", "end_time", "title"],
        },
    },
    {
        "name": "suggest_alternative_slots",
        "description": (
            "Sugere horários livres para os dois em uma data. "
            "Use quando o horário solicitado estiver ocupado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Data no formato YYYY-MM-DD"},
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duração desejada do evento em minutos",
                },
            },
            "required": ["date", "duration_minutes"],
        },
    },
]

TOOL_FUNCTIONS = {
    "check_husband_availability": check_husband_availability,
    "get_husband_schedule": get_husband_schedule,
    "get_my_schedule": get_my_schedule,
    "create_event": create_event,
    "suggest_alternative_slots": suggest_alternative_slots,
}

SYSTEM_PROMPT = f"""Você é o **AgendaBot**, assistente pessoal de agendamento.

Data de hoje: {TODAY}

Seu papel é gerenciar compromissos verificando **sempre** a disponibilidade do marido antes de incluí-lo em qualquer evento.

**Fluxo obrigatório para eventos com o marido:**
1. Chame `check_husband_availability` para o horário desejado
2. Se disponível → crie com `create_event` (include_husband=true)
3. Se indisponível → chame `suggest_alternative_slots` e apresente as opções ao usuário, pedindo para escolher antes de criar

Para eventos sem o marido, crie diretamente com `create_event` (include_husband=false).

**Diretrizes:**
- Responda sempre em português brasileiro
- Seja objetivo e confirme detalhes ambíguos antes de criar
- Para datas relativas ("amanhã", "sexta-feira"), converta usando a data de hoje: {TODAY}
- Ao sugerir horários alternativos, liste as opções e aguarde a escolha do usuário
"""


def call_tool(name: str, tool_input: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return json.dumps({"error": f"Ferramenta '{name}' não encontrada."})
    return json.dumps(func(**tool_input), ensure_ascii=False)


def run_agent_turn(client: anthropic.Anthropic, user_message: str) -> tuple[str, list[dict]]:
    """Executa um turno agêntico. Retorna (resposta_texto, chamadas_de_ferramentas)."""
    messages = list(st.session_state.conversation_history) + [
        {"role": "user", "content": user_message}
    ]
    tool_calls_log: list[dict] = []

    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next((b.text for b in response.content if b.type == "text"), "")
            st.session_state.conversation_history.append(
                {"role": "user", "content": user_message}
            )
            st.session_state.conversation_history.append(
                {"role": "assistant", "content": text}
            )
            return text, tool_calls_log

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = call_tool(block.name, block.input)
                    result_data = json.loads(result_str)
                    tool_calls_log.append({
                        "tool": block.name,
                        "input": block.input,
                        "result": result_data,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return "[Erro interno no agente]", []


# --- Interface Streamlit ---

st.set_page_config(
    page_title="AgendaBot 📅",
    page_icon="📅",
    layout="centered",
)

st.title("📅 AgendaBot")
st.caption(f"Assistente de agendamento com verificação da agenda do marido · Hoje: {TODAY}")

# Inicializa session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "scheduled_events" not in st.session_state:
    st.session_state.scheduled_events = []

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuração")
    api_key = st.text_input(
        "Chave da API Anthropic",
        type="password",
        placeholder="sk-ant-...",
        help="Obtenha sua chave em console.anthropic.com",
    )

    st.divider()
    st.markdown("**Exemplos de pedidos:**")
    suggestions = [
        "📆 Agenda de amanhã",
        "🍽️ Almoço com marido na quinta às 12h",
        "📋 Quando marido está livre essa semana?",
        "🏥 Consulta médica na sexta às 15h (só eu)",
        "☕ Café com amiga no sábado às 10h",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state.pending_suggestion = s

    st.divider()

    # Eventos agendados
    if st.session_state.scheduled_events:
        st.markdown("**Eventos agendados:**")
        for ev in st.session_state.scheduled_events:
            attendees = " + ".join(ev["attendees"])
            st.markdown(
                f"- **{ev['title']}**  \n"
                f"  {ev['date']} {ev['start']}–{ev['end']}  \n"
                f"  👥 {attendees}"
            )
        st.divider()

    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.session_state.scheduled_events = []
        st.rerun()

if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None

# Exibe histórico de mensagens
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "📅"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("tool_calls"):
            with st.expander("🔧 Ferramentas utilizadas"):
                for tc in msg["tool_calls"]:
                    st.markdown(f"**`{tc['tool']}`**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption("Entrada")
                        st.json(tc["input"])
                    with col2:
                        st.caption("Resultado")
                        st.json(tc["result"])

# Mensagem de boas-vindas
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="📅"):
        st.markdown(
            "Olá! Sou o **AgendaBot** 📅 Posso agendar compromissos para você, "
            "verificando automaticamente se seu marido está disponível antes de criar os convites. "
            "O que posso agendar para você?"
        )

# Captura input
user_input = None

if st.session_state.pending_suggestion:
    user_input = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None

typed = st.chat_input("Peça um agendamento ou consulte a agenda...")
if typed:
    user_input = typed

if user_input:
    effective_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not effective_api_key:
        st.error("Configure sua chave da API Anthropic na barra lateral para começar.")
        st.stop()

    # Exibe mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    # Gera resposta do agente
    with st.chat_message("assistant", avatar="📅"):
        with st.spinner("Consultando agenda..."):
            try:
                client = anthropic.Anthropic(api_key=effective_api_key)
                response_text, tool_calls = run_agent_turn(client, user_input)

                st.markdown(response_text)
                if tool_calls:
                    with st.expander("🔧 Ferramentas utilizadas"):
                        for tc in tool_calls:
                            st.markdown(f"**`{tc['tool']}`**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.caption("Entrada")
                                st.json(tc["input"])
                            with col2:
                                st.caption("Resultado")
                                st.json(tc["result"])

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "tool_calls": tool_calls,
                })

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
