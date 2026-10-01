from __future__ import annotations

import json
import streamlit as st

from director import direct_scene
from memory_engine import update_story_memory
from openrouter_client import OpenRouterError, chat
from prompts import build_system_prompt
from state import compact_state, new_state
from story_bible import STORY_BIBLE


st.set_page_config(page_title="Mary Core 2", page_icon="🖤", layout="centered")

DEFAULT_MODELS = [
    "anthropic/claude-sonnet-5.5",
    "z-ai/glm-5.3-prime",
    "qwen/qwen3.8-max-prime",
    "Outro...",
]

INITIAL_CANONICAL_MEMORY = """
FATOS E REVELAÇÕES
- Mary confessou a Janio que o traiu com Ricardo.

ESTADO ATUAL DA RELAÇÃO
- O casamento entre Mary e Janio é antigo, forte e está profundamente ferido pela traição.

FERIDAS / CONSEQUÊNCIAS ATIVAS
- A confiança de Janio em Mary foi abalada.
- Mary teme perder Janio e quer preservar o vínculo.

PENDÊNCIAS E VERDADES INCOMPLETAS
- Há aspectos da relação entre Mary e Ricardo que Janio ainda não conhece.
""".strip()

INITIAL_SCENE = {
    "location": "casa do casal",
    "time": "noite, pouco depois da confissão",
    "present_characters": ["MARY", "JANIO"],
    "user_role": "JANIO",
    "proximity": "mesmo ambiente, sem contato",
    "mary_immediate_goal": "fazer Janio permanecer na conversa",
    "event": "",
    "scene_changed": False,
    "show_caption": False,
    "scene_caption": "",
}

if "messages" not in st.session_state:
    st.session_state.messages = []
if "story_state" not in st.session_state:
    st.session_state.story_state = new_state()
if "canonical_memory" not in st.session_state:
    st.session_state.canonical_memory = INITIAL_CANONICAL_MEMORY
if "scene_state" not in st.session_state:
    st.session_state.scene_state = dict(INITIAL_SCENE)
if "turn_records" not in st.session_state:
    st.session_state.turn_records = []

st.title("Mary Core 2")
st.caption("Novela interativa: Mary, Janio e Ricardo.")

with st.sidebar:
    st.subheader("Você interpreta")
    user_role = st.radio(
        "Papel ativo",
        ["JANIO", "RICARDO"],
        horizontal=True,
    )

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
        model = st.text_input("ID do modelo", placeholder="provedor/modelo").strip()
    else:
        model = selected

    temperature = st.slider("Temperatura", 0.2, 1.3, 0.9, 0.1)

    if st.button("Reiniciar história", use_container_width=True):
        st.session_state.messages = []
        st.session_state.story_state = new_state()
        st.session_state.canonical_memory = INITIAL_CANONICAL_MEMORY
        st.session_state.scene_state = dict(INITIAL_SCENE)
        st.session_state.turn_records = []
        st.rerun()

    with st.expander("Cena atual"):
        st.json(st.session_state.scene_state)

    with st.expander("Memória canônica"):
        st.text(st.session_state.canonical_memory)

    with st.expander("Estado interno"):
        st.json(st.session_state.story_state)

for record in st.session_state.turn_records:
    if record.get("caption"):
        st.info(record["caption"])
    with st.chat_message(record["user_role"].lower()):
        st.markdown(record["user_text"])
    with st.chat_message("assistant"):
        st.markdown(record["mary_text"])

if not st.session_state.turn_records:
    st.info("Na casa do casal, pouco depois da confissão, Mary tenta impedir que Janio encerre a conversa.")
    with st.chat_message("assistant"):
        st.markdown("Janio... olha pra mim. Só... não vai embora ainda.")

placeholder = "Fale como Janio..." if user_role == "JANIO" else "Fale como Ricardo..."
user_text = st.chat_input(placeholder)

if user_text:
    try:
        if not model:
            raise OpenRouterError("Informe um ID de modelo do OpenRouter.")

        api_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
        fallback = str(st.secrets.get("MARY_FALLBACK_MODEL", "")).strip() or None
        director_model = str(st.secrets.get("MARY_DIRECTOR_MODEL", model)).strip() or model

        # Registra o turno bruto com marcação explícita do papel do usuário.
        st.session_state.messages.append(
            {"role": "user", "content": f"[PAPEL={user_role}] {user_text}"}
        )

        scene = direct_scene(
            api_key=api_key,
            model=director_model,
            fallback_model=fallback,
            story_bible=STORY_BIBLE,
            canonical_memory=st.session_state.canonical_memory,
            current_scene=st.session_state.scene_state,
            user_role=user_role,
            recent_messages=st.session_state.messages,
        )
        st.session_state.scene_state = scene

        scene_text = json.dumps(scene, ensure_ascii=False)
        system_prompt = build_system_prompt(
            story_bible=STORY_BIBLE,
            state_text=compact_state(st.session_state.story_state),
            canonical_memory=st.session_state.canonical_memory,
            scene_text=scene_text,
            user_role=user_role,
        )

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

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        caption = scene.get("scene_caption", "") if scene.get("show_caption") else ""

        st.session_state.turn_records.append(
            {
                "caption": caption,
                "user_role": user_role,
                "user_text": user_text,
                "mary_text": answer,
            }
        )

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

        st.rerun()

    except KeyError:
        st.error("OPENROUTER_API_KEY não encontrada em st.secrets.")
    except OpenRouterError as exc:
        st.error(f"Erro OpenRouter: {exc}")
    except Exception as exc:
        st.error(f"Erro inesperado: {exc}")
