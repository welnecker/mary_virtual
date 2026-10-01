from __future__ import annotations

import streamlit as st

from memory_engine import update_story_memory
from openrouter_client import OpenRouterError, chat
from prompts import build_system_prompt
from state import compact_state, new_state


st.set_page_config(page_title="Mary Core 2", page_icon="🖤", layout="centered")

DEFAULT_MODELS = [
    "anthropic/claude-sonnet-5.5",
    "z-ai/glm-5.3-prime",
    "qwen/qwen3.8-max-prime",
    "Outro...",
]

INITIAL_CANONICAL_MEMORY = """
FATOS E REVELAÇÕES
- Mary confessou ao marido que o traiu.

ESTADO ATUAL DA RELAÇÃO
- O casamento é antigo, forte e está profundamente ferido pela confissão.

FERIDAS / CONSEQUÊNCIAS ATIVAS
- A confiança do marido em Mary foi abalada.
- Mary teme perder o marido e quer preservar o vínculo.

PENDÊNCIAS E VERDADES INCOMPLETAS
- Há aspectos da traição que Mary ainda não contou.
""".strip()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "story_state" not in st.session_state:
    st.session_state.story_state = new_state()
if "canonical_memory" not in st.session_state:
    st.session_state.canonical_memory = INITIAL_CANONICAL_MEMORY

st.title("Mary Core 2")
st.caption("Laboratório de personalidade, memória e drama relacional.")

with st.sidebar:
    st.subheader("Modelo")

    configured_default = str(
        st.secrets.get("MARY_DEFAULT_MODEL", DEFAULT_MODELS[0])
    ).strip()

    choices = list(DEFAULT_MODELS)
    if configured_default and configured_default not in choices:
        choices.insert(0, configured_default)

    selected = st.selectbox(
        "OpenRouter",
        choices,
        index=choices.index(configured_default) if configured_default in choices else 0,
    )

    if selected == "Outro...":
        model = st.text_input(
            "ID do modelo",
            placeholder="provedor/modelo",
        ).strip()
    else:
        model = selected

    temperature = st.slider(
        "Temperatura",
        min_value=0.2,
        max_value=1.3,
        value=0.9,
        step=0.1,
    )

    if st.button("Reiniciar história", use_container_width=True):
        st.session_state.messages = []
        st.session_state.story_state = new_state()
        st.session_state.canonical_memory = INITIAL_CANONICAL_MEMORY
        st.rerun()

    with st.expander("Estado interno"):
        st.json(st.session_state.story_state)

    with st.expander("Memória canônica"):
        st.text(st.session_state.canonical_memory)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Eu contei. Não do jeito que devia, não na hora que devia... "
            "mas contei. Agora fala alguma coisa, porque esse seu silêncio tá me matando."
        )

user_text = st.chat_input("Você é o marido. O que diz a Mary?")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})

    with st.chat_message("user"):
        st.markdown(user_text)

    answer = None

    try:
        if not model:
            raise OpenRouterError("Informe um ID de modelo do OpenRouter.")

        api_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
        fallback = str(st.secrets.get("MARY_FALLBACK_MODEL", "")).strip() or None

        system_prompt = build_system_prompt(
            state_text=compact_state(st.session_state.story_state),
            canonical_memory=st.session_state.canonical_memory,
        )

        # A memória longa fica no system prompt.
        # O histórico cru é apenas a janela imediata, sem duplicação.
        llm_messages = [
            {"role": "system", "content": system_prompt},
            *st.session_state.messages[-12:],
        ]

        answer = chat(
            api_key=api_key,
            model=model,
            fallback_model=fallback,
            messages=llm_messages,
            temperature=temperature,
        )
    except KeyError:
        answer = (
            "Erro de configuração: OPENROUTER_API_KEY não encontrada em "
            "st.secrets. Veja mary2/.streamlit/secrets.toml.example."
        )
    except OpenRouterError as exc:
        answer = f"Erro OpenRouter: {exc}"
    except Exception as exc:
        answer = f"Erro inesperado: {exc}"

    st.session_state.messages.append({"role": "assistant", "content": answer})

    # Atualiza a memória depois do turno concluído. Se a atualização falhar,
    # o diálogo continua funcionando com a memória anterior.
    if answer and not answer.startswith("Erro"):
        try:
            memory_model = str(
                st.secrets.get("MARY_MEMORY_MODEL", model)
            ).strip() or model

            st.session_state.canonical_memory = update_story_memory(
                api_key=api_key,
                model=memory_model,
                fallback_model=fallback,
                current_memory=st.session_state.canonical_memory,
                recent_messages=st.session_state.messages[-8:],
            )
        except Exception:
            pass

    with st.chat_message("assistant"):
        st.markdown(answer)
