from __future__ import annotations

import json
from copy import deepcopy

import streamlit as st

from director import direct_scene
from input_router import parse_user_input
from memory_engine import update_story_memory
from openrouter_client import OpenRouterError, chat
from output_filter import sanitize_mary_output
from persistence import (
    PersistenceError,
    create_run,
    delete_interactions_from_seq,
    ensure_schema,
    load_latest_run,
    load_run_interactions,
    save_turn,
)
from prompts import build_system_prompt
from state import compact_state, migrate_state, new_state
from story_bible import STORY_BIBLE


st.set_page_config(page_title="Mary Core 2", page_icon="🖤", layout="centered")

DEFAULT_MODELS = [
    "google/gemini-2.5-flash-lite",
    "google/gemma-4-31b-it",
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
    "interaction_mode": "in_person",
    "user_role": "JANIO",
    "proximity": "mesmo ambiente, sem contato",
    "mary_immediate_goal": "fazer Janio permanecer na conversa",
    "mary_action": "",
    "open_hook": False,
    "hook_resolution": "",
    "temporary_character": {
        "active": False,
        "name": "",
        "description": "",
        "relation_to_mary": "",
        "user_can_play": False,
    },
    "return_anchor": "Mary e Janio continuam sendo o eixo principal da história.",
    "event": "",
    "scene_changed": False,
    "show_caption": False,
    "scene_caption": "",
    "arc_phase": "opening",
    "resolution_type": "none",
    "resolution_summary": "",
    "start_new_scene": False,
    "turns_in_scene": 0,
    "scene_number": 1,
}


def reset_local_story() -> None:
    st.session_state.messages = []
    st.session_state.story_state = new_state()
    st.session_state.canonical_memory = INITIAL_CANONICAL_MEMORY
    st.session_state.scene_state = dict(INITIAL_SCENE)
    st.session_state.turn_records = []
    st.session_state.active_user_role = "JANIO"


def persistence_config() -> dict | None:
    service_account = None

    # Compatibilidade com o secret já usado no projeto:
    # GOOGLE_CREDS_JSON pode ser uma string JSON completa.
    try:
        raw_creds = st.secrets.get("GOOGLE_CREDS_JSON", "")
        if raw_creds:
            if isinstance(raw_creds, str):
                service_account = json.loads(raw_creds)
            else:
                service_account = dict(raw_creds)
    except Exception:
        service_account = None

    # Fallback opcional para configuração TOML estruturada.
    if not service_account:
        try:
            service_account = dict(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        except Exception:
            service_account = None

    if not service_account:
        return None

    # Corrige quebras de linha escapadas na private_key quando necessário.
    private_key = service_account.get("private_key")
    if isinstance(private_key, str):
        service_account["private_key"] = private_key.replace("\\n", "\n")

    return {
        "service_account_info": service_account,
        "spreadsheet_id": str(st.secrets.get("MARY_SHEETS_ID", "")).strip(),
        "spreadsheet_title": str(
            st.secrets.get("MARY_SHEETS_TITLE", "MARY_CORE_PERSISTENCE")
        ).strip() or "MARY_CORE_PERSISTENCE",
        "owner_email": str(st.secrets.get("MARY_SHEETS_OWNER_EMAIL", "")).strip(),
        "player_id": str(st.secrets.get("MARY_PLAYER_ID", "janio")).strip() or "janio",
    }


def reconstruct_legacy_snapshot(
    *,
    persistence: dict,
    run_id: str,
    before_seq: int,
    api_key: str,
    director_model: str,
    memory_model: str,
    fallback_model: str | None,
) -> dict:
    """Reconstrói o estado imediatamente anterior a uma interação antiga."""

    rows = load_run_interactions(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=run_id,
    )

    rows = [
        row
        for row in rows
        if int(row.get("seq", 0) or 0) < int(before_seq)
    ]

    scene_state = dict(INITIAL_SCENE)
    story_state = new_state()
    canonical_memory = INITIAL_CANONICAL_MEMORY
    messages: list[dict[str, str]] = []
    active_role = "JANIO"

    for row in rows:
        role = str(row.get("user_role", "JANIO") or "JANIO").upper()
        if role == "RICARDO":
            # Compatibilidade com runs antigas: Ricardo passa a ser tratado
            # como personagem circunstancial, não como papel principal.
            role = "PERSONAGEM_DA_CENA"
            scene_state["temporary_character"] = {
                "active": True,
                "name": "Ricardo",
                "description": "personagem ligado ao passado da crise",
                "relation_to_mary": "conhecido do passado",
                "user_can_play": True,
            }
        elif role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
            role = "JANIO"

        direction = str(row.get("scene_direction", "") or "").strip()
        user_text = str(row.get("user_text", "") or "").strip()
        mary_text = str(row.get("mary_text", "") or "").strip()
        user_spoke = bool(user_text)

        if user_spoke:
            messages.append(
                {"role": "user", "content": f"[PAPEL={role}] {user_text}"}
            )

        scene_state = direct_scene(
            api_key=api_key,
            model=director_model,
            fallback_model=fallback_model,
            story_bible=STORY_BIBLE,
            canonical_memory=canonical_memory,
            current_scene=scene_state,
            user_role=role,
            recent_messages=messages,
            scene_direction=direction,
            user_spoke=user_spoke,
        )

        if mary_text:
            messages.append({"role": "assistant", "content": mary_text})

            canonical_memory = update_story_memory(
                api_key=api_key,
                model=memory_model,
                fallback_model=fallback_model,
                current_memory=canonical_memory,
                recent_messages=messages[-10:],
            )

        active_role = role

    return {
        "active_user_role": active_role,
        "canonical_memory": canonical_memory,
        "scene_state": scene_state,
        "story_state": story_state,
    }


for key, default in {
    "messages": [],
    "story_state": new_state(),
    "canonical_memory": INITIAL_CANONICAL_MEMORY,
    "scene_state": dict(INITIAL_SCENE),
    "turn_records": [],
    "run_id": "",
    "active_user_role": "JANIO",
    "persistence_loaded": False,
    "persistence_error": "",
    "spreadsheet_url": "",
    "rollback_notice": "",
    "rollback_retry_text": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# Recupera a história uma única vez por sessão Streamlit.
persistence = persistence_config()
if persistence and not st.session_state.persistence_loaded:
    try:
        info = ensure_schema(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
        )
        st.session_state.spreadsheet_url = info["spreadsheet_url"]

        saved = load_latest_run(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=info["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            player_id=persistence["player_id"],
            interaction_limit=30,
        )

        if saved:
            st.session_state.run_id = saved["run_id"]
            st.session_state.active_user_role = saved["active_user_role"]
            st.session_state.canonical_memory = (
                saved["canonical_memory"] or INITIAL_CANONICAL_MEMORY
            )
            st.session_state.scene_state = saved["scene_state"] or dict(INITIAL_SCENE)
            st.session_state.story_state = migrate_state(saved["story_state"])
            st.session_state.turn_records = saved["turn_records"]
            st.session_state.messages = saved["messages"]
        else:
            st.session_state.run_id = create_run(
                service_account_info=persistence["service_account_info"],
                spreadsheet_id=info["spreadsheet_id"],
                spreadsheet_title=persistence["spreadsheet_title"],
                owner_email=persistence["owner_email"],
                player_id=persistence["player_id"],
                active_user_role=st.session_state.active_user_role,
                canonical_memory=st.session_state.canonical_memory,
                scene_state=st.session_state.scene_state,
                story_state=st.session_state.story_state,
                archive_previous=False,
            )

        st.session_state.persistence_loaded = True
        st.session_state.persistence_error = ""
    except Exception as exc:
        st.session_state.persistence_loaded = True
        st.session_state.persistence_error = str(exc)


st.title("Mary Core 2")
st.caption("Novela interativa aberta: Mary e Janio no centro, o mundo ao redor em movimento.")

if st.session_state.rollback_notice:
    st.success(st.session_state.rollback_notice)
    st.session_state.rollback_notice = ""
    if st.session_state.rollback_retry_text:
        st.caption("Fala removida para você reenviar com o prompt atualizado:")
        st.code(st.session_state.rollback_retry_text)

with st.sidebar:
    st.subheader("Você interpreta")

    temporary_character = st.session_state.scene_state.get(
        "temporary_character",
        {},
    )
    if not isinstance(temporary_character, dict):
        temporary_character = {}

    role_options = ["JANIO"]
    temporary_available = bool(
        temporary_character.get("active")
        and temporary_character.get("user_can_play")
        and str(temporary_character.get("name", "") or "").strip()
    )
    if temporary_available:
        role_options.append("PERSONAGEM_DA_CENA")

    current_role = st.session_state.active_user_role
    if current_role not in role_options:
        current_role = "JANIO"

    def _role_label(value: str) -> str:
        if value == "JANIO":
            return "Janio"
        name = str(temporary_character.get("name", "") or "").strip()
        return name or "Personagem da cena"

    user_role = st.radio(
        "Papel ativo",
        role_options,
        index=role_options.index(current_role),
        horizontal=True,
        format_func=_role_label,
    )
    st.session_state.active_user_role = user_role

    if temporary_available:
        description = str(
            temporary_character.get("description", "") or ""
        ).strip()
        relation = str(
            temporary_character.get("relation_to_mary", "") or ""
        ).strip()
        details = " · ".join(
            item for item in [description, relation] if item
        )
        if details:
            st.caption(
                f"Personagem da cena: {_role_label('PERSONAGEM_DA_CENA')} — {details}"
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

    if st.button("Nova história", use_container_width=True):
        reset_local_story()

        if persistence:
            try:
                info = ensure_schema(
                    service_account_info=persistence["service_account_info"],
                    spreadsheet_id=persistence["spreadsheet_id"],
                    spreadsheet_title=persistence["spreadsheet_title"],
                    owner_email=persistence["owner_email"],
                )
                st.session_state.spreadsheet_url = info["spreadsheet_url"]
                st.session_state.run_id = create_run(
                    service_account_info=persistence["service_account_info"],
                    spreadsheet_id=info["spreadsheet_id"],
                    spreadsheet_title=persistence["spreadsheet_title"],
                    owner_email=persistence["owner_email"],
                    player_id=persistence["player_id"],
                    active_user_role="JANIO",
                    canonical_memory=INITIAL_CANONICAL_MEMORY,
                    scene_state=dict(INITIAL_SCENE),
                    story_state=new_state(),
                    archive_previous=True,
                )
                st.session_state.persistence_error = ""
            except Exception as exc:
                st.session_state.persistence_error = str(exc)

        st.rerun()

    if persistence and not st.session_state.persistence_error:
        st.success("História persistente ativa")
        if st.session_state.spreadsheet_url:
            st.markdown(f"[Abrir planilha de memória]({st.session_state.spreadsheet_url})")
        if st.session_state.run_id:
            st.caption(f"Run: {st.session_state.run_id}")
    elif st.session_state.persistence_error:
        st.warning("Persistência indisponível nesta sessão.")
        with st.expander("Detalhe técnico"):
            st.code(st.session_state.persistence_error)
    else:
        st.caption("Persistência Google Sheets ainda não configurada.")

    if (
        persistence
        and st.session_state.run_id
        and st.session_state.turn_records
        and not st.session_state.persistence_error
    ):
        with st.expander("Corrigir interações"):
            rewindable = [
                record
                for record in st.session_state.turn_records
                if int(record.get("seq", 0) or 0) > 0
            ]

            if rewindable:
                rewindable = list(reversed(rewindable))

                def _rollback_label(record: dict) -> str:
                    seq = int(record.get("seq", 0) or 0)
                    role = str(record.get("user_role", "") or "")
                    user_preview = str(
                        record.get("user_text")
                        or record.get("direction")
                        or "(direção de cena)"
                    ).replace("\n", " ").strip()
                    mary_preview = str(record.get("mary_text", "") or "").replace(
                        "\n", " "
                    ).strip()
                    if len(user_preview) > 42:
                        user_preview = user_preview[:39] + "..."
                    if len(mary_preview) > 42:
                        mary_preview = mary_preview[:39] + "..."
                    return f"#{seq} · {role}: {user_preview} → Mary: {mary_preview}"

                selected_record = st.selectbox(
                    "Voltar até antes de qual resposta?",
                    rewindable,
                    format_func=_rollback_label,
                    key="rollback_selected_record",
                )

                st.caption(
                    "A interação escolhida e todas as posteriores serão apagadas. "
                    "Memória, cena e estado voltam ao ponto imediatamente anterior."
                )
                confirm_rollback = st.checkbox(
                    "Confirmo que quero apagar deste ponto em diante",
                    key="confirm_rollback",
                )

                if st.button(
                    "Voltar até antes desta interação",
                    use_container_width=True,
                    disabled=not confirm_rollback,
                ):
                    selected_seq = int(selected_record.get("seq", 0) or 0)
                    retry_text = str(
                        selected_record.get("user_text")
                        or selected_record.get("direction")
                        or ""
                    ).strip()

                    try:
                        api_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
                        fallback = str(
                            st.secrets.get("MARY_FALLBACK_MODEL", "")
                        ).strip() or None
                        director_model = str(
                            st.secrets.get("MARY_DIRECTOR_MODEL", model)
                        ).strip() or model
                        memory_model = str(
                            st.secrets.get("MARY_MEMORY_MODEL", model)
                        ).strip() or model

                        selected_rows = load_run_interactions(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                        )
                        selected_sheet_record = next(
                            (
                                row
                                for row in selected_rows
                                if int(row.get("seq", 0) or 0) == selected_seq
                            ),
                            {},
                        )

                        fallback_snapshot = None
                        if not str(
                            selected_sheet_record.get(
                                "canonical_memory_before",
                                "",
                            )
                            or ""
                        ).strip():
                            with st.spinner(
                                "Reconstruindo o estado anterior desta interação..."
                            ):
                                fallback_snapshot = reconstruct_legacy_snapshot(
                                    persistence=persistence,
                                    run_id=st.session_state.run_id,
                                    before_seq=selected_seq,
                                    api_key=api_key,
                                    director_model=director_model,
                                    memory_model=memory_model,
                                    fallback_model=fallback,
                                )

                        delete_interactions_from_seq(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            from_seq=selected_seq,
                            fallback_snapshot=fallback_snapshot,
                        )

                        saved = load_latest_run(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            player_id=persistence["player_id"],
                            interaction_limit=30,
                        )
                        if not saved:
                            raise PersistenceError(
                                "A run não pôde ser recarregada após o rollback."
                            )

                        st.session_state.run_id = saved["run_id"]
                        st.session_state.active_user_role = saved["active_user_role"]
                        st.session_state.canonical_memory = (
                            saved["canonical_memory"] or INITIAL_CANONICAL_MEMORY
                        )
                        st.session_state.scene_state = (
                            saved["scene_state"] or dict(INITIAL_SCENE)
                        )
                        st.session_state.story_state = migrate_state(
                            saved["story_state"]
                        )
                        st.session_state.turn_records = saved["turn_records"]
                        st.session_state.messages = saved["messages"]
                        st.session_state.persistence_error = ""
                        st.session_state.rollback_notice = (
                            f"História restaurada para antes da interação #{selected_seq}."
                        )
                        st.session_state.rollback_retry_text = retry_text
                        st.rerun()
                    except Exception as exc:
                        st.session_state.persistence_error = str(exc)
                        st.error(f"Não foi possível corrigir a interação: {exc}")
            else:
                st.caption("Não há interações disponíveis para correção nesta run.")

    with st.expander("Cena atual"):
        st.json(st.session_state.scene_state)

    with st.expander("Memória canônica"):
        st.text(st.session_state.canonical_memory)

    with st.expander("Estado interno"):
        st.json(st.session_state.story_state)


for record in st.session_state.turn_records:
    if record.get("direction"):
        st.caption("🎬 " + record["direction"])
    if record.get("caption"):
        st.info(record["caption"])
    if record.get("hook_resolution"):
        st.info(record["hook_resolution"])
    if record.get("mary_action"):
        st.markdown(f"*{record['mary_action']}*")
    if record.get("user_text"):
        with st.chat_message("user"):
            record_role = str(record.get("user_role", "JANIO") or "JANIO")
            if record_role == "PERSONAGEM_DA_CENA":
                st.caption("Personagem da cena")
            else:
                st.caption("Janio")
            st.markdown(record["user_text"])
    with st.chat_message("assistant"):
        st.markdown(record["mary_text"])


if not st.session_state.turn_records:
    st.info(
        "Na casa do casal, pouco depois da confissão, "
        "Mary tenta impedir que Janio encerre a conversa."
    )
    with st.chat_message("assistant"):
        st.markdown("Janio... olha pra mim. Só... não vai embora ainda.")


if user_role == "JANIO":
    placeholder = "Fale ou dirija a cena como Janio..."
else:
    temporary_name = str(
        st.session_state.scene_state.get("temporary_character", {}).get("name", "")
        or "personagem da cena"
    ).strip()
    placeholder = f"Fale ou dirija a cena como {temporary_name}..."
user_text = st.chat_input(placeholder)


if user_text:
    try:
        if not model:
            raise OpenRouterError("Informe um ID de modelo do OpenRouter.")

        api_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
        fallback = str(st.secrets.get("MARY_FALLBACK_MODEL", "")).strip() or None
        director_model = str(st.secrets.get("MARY_DIRECTOR_MODEL", model)).strip() or model
        input_model = str(st.secrets.get("MARY_INPUT_MODEL", director_model)).strip() or director_model

        previous_scene_role = str(
            st.session_state.scene_state.get(
                "user_role",
                st.session_state.active_user_role,
            )
            or "JANIO"
        ).upper()
        pre_turn_snapshot = {
            "active_user_role": previous_scene_role,
            "canonical_memory": st.session_state.canonical_memory,
            "scene_state": deepcopy(st.session_state.scene_state),
            "story_state": deepcopy(st.session_state.story_state),
        }

        parsed_input = parse_user_input(
            api_key=api_key,
            model=input_model,
            fallback_model=fallback,
            user_role=user_role,
            raw_text=user_text,
        )
        scene_direction = parsed_input["scene_direction"]
        dialogue_text = parsed_input["dialogue"]
        user_spoke = bool(dialogue_text)
        st.session_state.rollback_retry_text = ""

        messages_before_turn = deepcopy(st.session_state.messages)

        if user_spoke:
            st.session_state.messages.append(
                {"role": "user", "content": f"[PAPEL={user_role}] {dialogue_text}"}
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
            scene_direction=scene_direction,
            user_spoke=user_spoke,
        )

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

        try:
            raw_answer = chat(
                api_key=api_key,
                model=model,
                fallback_model=fallback,
                messages=llm_messages,
                temperature=temperature,
            )
            answer = sanitize_mary_output(raw_answer)

            if not answer:
                retry_messages = [
                    *llm_messages,
                    {
                        "role": "system",
                        "content": (
                            "CORREÇÃO DE FORMATO: sua resposta anterior continha apenas "
                            "rubrica/narração e foi descartada. Responda novamente SOMENTE "
                            "com a fala verbal de Mary, em primeira pessoa, sem asteriscos, "
                            "sem narração e sem descrever ações."
                        ),
                    },
                ]
                raw_answer = chat(
                    api_key=api_key,
                    model=model,
                    fallback_model=fallback,
                    messages=retry_messages,
                    temperature=max(0.2, min(float(temperature), 0.8)),
                )
                answer = sanitize_mary_output(raw_answer)

            if not answer:
                raise OpenRouterError(
                    "O modelo não produziu fala verbal de Mary após duas tentativas."
                )
        except Exception:
            # Turno atômico: nada da tentativa incompleta fica na sessão.
            st.session_state.scene_state = deepcopy(
                pre_turn_snapshot["scene_state"]
            )
            st.session_state.messages = messages_before_turn
            raise

        # Só confirma a cena depois que Mary respondeu de fato.
        st.session_state.scene_state = scene
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        caption = scene.get("scene_caption", "") if scene.get("show_caption") else ""

        turn_record = {
            "seq": 0,
            "caption": caption,
            "direction": scene_direction,
            "mary_action": str(scene.get("mary_action", "") or "").strip(),
            "hook_resolution": str(scene.get("hook_resolution", "") or "").strip(),
            "user_role": user_role,
            "user_text": dialogue_text,
            "mary_text": answer,
        }
        st.session_state.turn_records.append(turn_record)

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
                    recent_messages=st.session_state.messages[-10:],
                )
            except Exception:
                pass

        # Persiste depois da memória canônica ser atualizada.
        if persistence:
            try:
                info = ensure_schema(
                    service_account_info=persistence["service_account_info"],
                    spreadsheet_id=persistence["spreadsheet_id"],
                    spreadsheet_title=persistence["spreadsheet_title"],
                    owner_email=persistence["owner_email"],
                )
                st.session_state.spreadsheet_url = info["spreadsheet_url"]

                if not st.session_state.run_id:
                    st.session_state.run_id = create_run(
                        service_account_info=persistence["service_account_info"],
                        spreadsheet_id=info["spreadsheet_id"],
                        spreadsheet_title=persistence["spreadsheet_title"],
                        owner_email=persistence["owner_email"],
                        player_id=persistence["player_id"],
                        active_user_role=user_role,
                        canonical_memory=st.session_state.canonical_memory,
                        scene_state=st.session_state.scene_state,
                        story_state=st.session_state.story_state,
                        archive_previous=False,
                    )

                saved_seq = save_turn(
                    service_account_info=persistence["service_account_info"],
                    spreadsheet_id=info["spreadsheet_id"],
                    spreadsheet_title=persistence["spreadsheet_title"],
                    owner_email=persistence["owner_email"],
                    run_id=st.session_state.run_id,
                    player_id=persistence["player_id"],
                    active_user_role=user_role,
                    canonical_memory=st.session_state.canonical_memory,
                    scene_state=st.session_state.scene_state,
                    story_state=st.session_state.story_state,
                    turn_record=turn_record,
                    pre_turn_snapshot=pre_turn_snapshot,
                )
                turn_record["seq"] = saved_seq
                st.session_state.persistence_error = ""
            except Exception as exc:
                # A história continua funcionando mesmo se o Google falhar.
                st.session_state.persistence_error = str(exc)

        st.rerun()

    except KeyError:
        st.error("OPENROUTER_API_KEY não encontrada em st.secrets.")
    except OpenRouterError as exc:
        st.error(f"Erro OpenRouter: {exc}")
    except PersistenceError as exc:
        st.error(f"Erro de persistência: {exc}")
    except Exception as exc:
        st.error(f"Erro inesperado: {exc}")
