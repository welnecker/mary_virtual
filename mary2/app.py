from __future__ import annotations

import json
import re
from copy import deepcopy

import streamlit as st

from chapters import (
    apply_choice_to_story,
    chapter_choices,
    chapter_phase,
    chapter_prompt,
    chapter_ready_for_choice,
    find_choice,
    get_chapter,
)
from director import direct_scene
from input_router import parse_user_input
from openrouter_client import OpenRouterError, chat
from output_filter import looks_like_action_narration, parse_mary_response, sanitize_mary_output
from persistence import (
    PersistenceError,
    create_run,
    delete_interactions_from_seq,
    ensure_schema,
    load_latest_run,
    load_run_interactions,
    load_checkpoint,
    load_checkpoints,
    new_branch_id,
    new_chapter_instance_id,
    save_branch,
    save_checkpoint,
    save_director_audit,
    save_turn,
    update_run_snapshot,
)
from prompts import build_system_prompt
from state import current_status_text, migrate_state, new_state, story_ledger_text
from story_bible import PHYSICAL_CANON


st.set_page_config(page_title="Mary Core 2", page_icon="🖤", layout="centered")

BUILD_ID = "2026-10-02-proactive-gym-v27"

DEFAULT_MODELS = [
    "google/gemini-2.5-flash-lite",
    "google/gemma-4-31b-it",
    "Outro...",
]

INITIAL_SCENE = deepcopy(
    get_chapter("confissao_inicial").get("initial_scene", {})
)


def _mary_display_text(text: str) -> str:
    """Cria respiro visual sem alterar a fala persistida nem o contexto da LLM."""
    value = str(text or "").strip()
    if not value:
        return ""

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?…])\s+", value)
        if part.strip()
    ]
    if len(sentences) <= 2 and len(value) <= 180:
        return value

    paragraphs: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        projected = current_len + (1 if current else 0) + len(sentence)
        if current and (len(current) >= 2 or projected > 180):
            paragraphs.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len = projected

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def reset_local_story() -> None:
    st.session_state.messages = []
    st.session_state.story_state = new_state()
    st.session_state.scene_state = deepcopy(INITIAL_SCENE)
    st.session_state.turn_records = []
    st.session_state.active_user_role = "JANIO"
    st.session_state.run_last_seq = 0


def _messages_from_records(records: list[dict]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for record in records:
        if record.get("user_text"):
            messages.append({
                "role": "user",
                "content": (
                    f"[PAPEL={record.get('user_role', 'JANIO')}] "
                    f"{record.get('user_text', '')}"
                ),
            })
        if record.get("mary_text"):
            messages.append({
                "role": "assistant",
                "content": str(record.get("mary_text", "") or ""),
            })
    return messages


def _handoff_from_record(record: dict | None) -> dict:
    if not isinstance(record, dict):
        return {}
    return {
        "user_role": str(record.get("user_role", "") or "").strip(),
        "user_text": str(record.get("user_text", "") or "").strip(),
        "mary_text": str(record.get("mary_text", "") or "").strip(),
        "mary_action": str(record.get("mary_action", "") or "").strip(),
    }


def _handoff_text(state: dict) -> str:
    narrative = state.get("narrative", {}) if isinstance(state, dict) else {}
    handoff = narrative.get("handoff", {}) if isinstance(narrative, dict) else {}
    if not isinstance(handoff, dict) or not any(str(v or "").strip() for v in handoff.values()):
        return "(nenhum)"
    parts = []
    user_text = str(handoff.get("user_text", "") or "").strip()
    mary_text = str(handoff.get("mary_text", "") or "").strip()
    mary_action = str(handoff.get("mary_action", "") or "").strip()
    user_role = str(handoff.get("user_role", "") or "").strip()
    if user_text:
        parts.append(f"Última fala de {user_role or 'USUÁRIO'}: {user_text}")
    if mary_action:
        parts.append(f"Última ação de Mary: {mary_action}")
    if mary_text:
        parts.append(f"Última fala de Mary: {mary_text}")
    return "\n".join(parts) or "(nenhum)"


def _scene_for_chapter_transition(chapter: dict, previous_scene: dict) -> dict:
    initial = deepcopy(chapter.get("initial_scene", {}) or {})
    if not bool(chapter.get("inherit_scene", False)):
        return initial

    previous = deepcopy(previous_scene or {})
    scene = previous

    # Micropassos herdam a identidade e o espaço reais da cena.
    inherited_keys = {
        "location",
        "time",
        "present_characters",
        "interaction_mode",
        "user_role",
        "temporary_character",
        "return_anchor",
    }

    for key, value in initial.items():
        if key not in inherited_keys:
            scene[key] = deepcopy(value)

    scene["scene_number"] = int(previous.get("scene_number", 1) or 1) + 1
    scene["turns_in_scene"] = 0
    scene["start_new_scene"] = True
    return scene


def _chapter_id() -> str:
    narrative = st.session_state.story_state.get("narrative", {})
    return str(narrative.get("chapter_id", "confissao_inicial") or "confissao_inicial")


def _chapter_turns() -> int:
    narrative = st.session_state.story_state.get("narrative", {})
    return int(narrative.get("chapter_turns", 0) or 0)


def activate_chapter(
    *,
    next_chapter_id: str,
    choice_id: str,
    persistence: dict | None,
) -> None:
    previous_chapter_id = _chapter_id()
    choice = find_choice(previous_chapter_id, choice_id)
    if not choice:
        raise ValueError(f"Escolha inválida para o capítulo {previous_chapter_id}: {choice_id}")

    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)
    previous_state = deepcopy(st.session_state.story_state)
    previous_scene = deepcopy(st.session_state.scene_state)
    previous_narrative = previous_state.setdefault("narrative", {})
    previous_branch_id = str(previous_narrative.get("branch_id", "main") or "main")
    previous_instance_id = str(
        previous_narrative.get("chapter_instance_id", "")
        or f"{previous_chapter_id}_legacy"
    )

    decision_checkpoint_id = ""
    if persistence and st.session_state.run_id:
        decision_checkpoint_id = save_checkpoint(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            checkpoint_type="decision",
            source_seq=last_seq,
            source_chapter_id=previous_chapter_id,
            source_chapter_instance_id=previous_instance_id,
            source_branch_id=previous_branch_id,
            choice_point_id=previous_chapter_id,
            active_user_role=st.session_state.active_user_role,
            story_ledger=story_ledger_text(previous_state),
            scene_state=previous_scene,
            story_state=previous_state,
        )

    st.session_state.story_state = apply_choice_to_story(
        story_state=previous_state,
        chapter_id=previous_chapter_id,
        choice_id=choice_id,
    )

    handoff = {}
    if bool(choice.get("carry_handoff", False)) and st.session_state.turn_records:
        handoff = _handoff_from_record(st.session_state.turn_records[-1])

    branch_id = new_branch_id(choice_id)
    chapter_instance_id = new_chapter_instance_id(next_chapter_id)
    narrative = st.session_state.story_state.setdefault("narrative", {})
    narrative["chapter_id"] = next_chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    narrative["chapter_start_seq"] = last_seq + 1
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["last_choice_id"] = choice_id
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = handoff
    narrative["parent_branch_id"] = previous_branch_id
    narrative["branch_id"] = branch_id
    narrative["parent_checkpoint_id"] = decision_checkpoint_id
    narrative["chapter_instance_id"] = chapter_instance_id
    narrative["chapter_entry_checkpoint_id"] = ""

    chapter = get_chapter(next_chapter_id)
    st.session_state.scene_state = _scene_for_chapter_transition(
        chapter,
        previous_scene,
    )

    next_role = str(
        st.session_state.scene_state.get("user_role", "JANIO") or "JANIO"
    ).upper()
    if next_role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
        next_role = "JANIO"
    st.session_state.active_user_role = next_role
    st.session_state.messages = []
    st.session_state.turn_records = []

    if persistence and st.session_state.run_id:
        save_branch(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            branch_id=branch_id,
            parent_branch_id=previous_branch_id,
            parent_checkpoint_id=decision_checkpoint_id,
            choice_id=choice_id,
            choice_label=str(choice.get("label", choice_id) or choice_id),
            chapter_id=next_chapter_id,
            chapter_instance_id=chapter_instance_id,
        )
        entry_checkpoint_id = save_checkpoint(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            checkpoint_type="chapter_entry",
            source_seq=last_seq,
            source_chapter_id=next_chapter_id,
            source_chapter_instance_id=chapter_instance_id,
            source_branch_id=branch_id,
            choice_point_id=next_chapter_id,
            active_user_role=st.session_state.active_user_role,
            story_ledger=story_ledger_text(st.session_state.story_state),
            scene_state=st.session_state.scene_state,
            story_state=st.session_state.story_state,
        )
        narrative["chapter_entry_checkpoint_id"] = entry_checkpoint_id

        update_run_snapshot(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            active_user_role=st.session_state.active_user_role,
            story_ledger=story_ledger_text(st.session_state.story_state),
            scene_state=st.session_state.scene_state,
            story_state=st.session_state.story_state,
        )

    st.rerun()



def restart_current_chapter(persistence: dict | None) -> None:
    """Cria nova instância do capítulo atual sem apagar interações anteriores."""
    if not persistence or not st.session_state.run_id:
        raise PersistenceError("Persistência necessária para reiniciar o capítulo sem apagar histórico.")

    narrative_now = st.session_state.story_state.setdefault("narrative", {})
    chapter_id = _chapter_id()
    branch_id = str(narrative_now.get("branch_id", "main") or "main")
    entry_checkpoint_id = str(
        narrative_now.get("chapter_entry_checkpoint_id", "") or ""
    ).strip()

    entry_story = None
    entry_scene = None
    entry_role = st.session_state.active_user_role

    if entry_checkpoint_id:
        checkpoint = load_checkpoint(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            checkpoint_id=entry_checkpoint_id,
        )
        entry_story = deepcopy(checkpoint["story_state"])
        entry_scene = deepcopy(checkpoint["scene_state"])
        entry_role = str(checkpoint.get("active_user_role", entry_role) or entry_role).upper()
    else:
        # Compatibilidade com capítulos criados antes da arquitetura de checkpoints.
        start_seq = int(narrative_now.get("chapter_start_seq", 1) or 1)
        rows = load_run_interactions(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
        )
        first_row = next(
            (row for row in rows if int(row.get("seq", 0) or 0) == start_seq),
            None,
        )
        if first_row:
            try:
                entry_story = json.loads(str(first_row.get("story_state_json_before", "") or "{}"))
                entry_scene = json.loads(str(first_row.get("scene_json_before", "") or "{}"))
            except Exception:
                entry_story = None
                entry_scene = None
            entry_role = str(
                first_row.get("active_user_role_before", entry_role) or entry_role
            ).upper()

    if not isinstance(entry_story, dict) or not isinstance(entry_scene, dict):
        raise PersistenceError(
            "Não foi possível localizar o estado de entrada deste capítulo."
        )

    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)
    new_instance_id = new_chapter_instance_id(chapter_id)
    restored = migrate_state(entry_story)
    narrative = restored.setdefault("narrative", {})
    narrative["chapter_id"] = chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    narrative["chapter_start_seq"] = last_seq + 1
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["branch_id"] = branch_id
    narrative["chapter_instance_id"] = new_instance_id
    narrative["chapter_entry_checkpoint_id"] = ""
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = {}
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    st.session_state.story_state = restored
    st.session_state.scene_state = deepcopy(entry_scene)
    st.session_state.active_user_role = (
        entry_role if entry_role in {"JANIO", "PERSONAGEM_DA_CENA"} else "JANIO"
    )
    st.session_state.messages = []
    st.session_state.turn_records = []

    new_entry_checkpoint_id = save_checkpoint(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        checkpoint_type="chapter_entry",
        source_seq=last_seq,
        source_chapter_id=chapter_id,
        source_chapter_instance_id=new_instance_id,
        source_branch_id=branch_id,
        choice_point_id=chapter_id,
        active_user_role=st.session_state.active_user_role,
        story_ledger=story_ledger_text(st.session_state.story_state),
        scene_state=st.session_state.scene_state,
        story_state=st.session_state.story_state,
    )
    narrative["chapter_entry_checkpoint_id"] = new_entry_checkpoint_id

    update_run_snapshot(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        active_user_role=st.session_state.active_user_role,
        story_ledger=story_ledger_text(st.session_state.story_state),
        scene_state=st.session_state.scene_state,
        story_state=st.session_state.story_state,
    )
    st.rerun()


def activate_choice_from_checkpoint(
    *,
    checkpoint_id: str,
    choice_id: str,
    persistence: dict,
) -> None:
    """Abre outra rota a partir de uma decisão antiga sem apagar a rota existente."""
    checkpoint = load_checkpoint(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        checkpoint_id=checkpoint_id,
    )
    source_chapter_id = str(checkpoint.get("source_chapter_id", "") or "")
    choice = find_choice(source_chapter_id, choice_id)
    if not choice:
        raise ValueError("Escolha não existe no checkpoint selecionado.")

    base_state = migrate_state(checkpoint["story_state"])
    base_scene = deepcopy(checkpoint["scene_state"])
    base_narrative = base_state.setdefault("narrative", {})
    parent_branch_id = str(
        checkpoint.get("source_branch_id", "")
        or base_narrative.get("branch_id", "main")
        or "main"
    )
    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)

    next_chapter_id = str(choice.get("next_chapter", "") or "")
    branch_id = new_branch_id(choice_id)
    instance_id = new_chapter_instance_id(next_chapter_id)

    next_state = apply_choice_to_story(
        story_state=base_state,
        chapter_id=source_chapter_id,
        choice_id=choice_id,
    )
    narrative = next_state.setdefault("narrative", {})
    narrative["chapter_id"] = next_chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    narrative["chapter_start_seq"] = last_seq + 1
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["last_choice_id"] = choice_id
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = {}
    narrative["parent_branch_id"] = parent_branch_id
    narrative["branch_id"] = branch_id
    narrative["parent_checkpoint_id"] = checkpoint_id
    narrative["chapter_instance_id"] = instance_id
    narrative["chapter_entry_checkpoint_id"] = ""
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    chapter = get_chapter(next_chapter_id)
    next_scene = _scene_for_chapter_transition(chapter, base_scene)
    next_role = str(next_scene.get("user_role", "JANIO") or "JANIO").upper()
    if next_role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
        next_role = "JANIO"

    st.session_state.story_state = next_state
    st.session_state.scene_state = next_scene
    st.session_state.active_user_role = next_role
    st.session_state.messages = []
    st.session_state.turn_records = []

    save_branch(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        branch_id=branch_id,
        parent_branch_id=parent_branch_id,
        parent_checkpoint_id=checkpoint_id,
        choice_id=choice_id,
        choice_label=str(choice.get("label", choice_id) or choice_id),
        chapter_id=next_chapter_id,
        chapter_instance_id=instance_id,
    )
    entry_id = save_checkpoint(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        checkpoint_type="chapter_entry",
        source_seq=last_seq,
        source_chapter_id=next_chapter_id,
        source_chapter_instance_id=instance_id,
        source_branch_id=branch_id,
        choice_point_id=next_chapter_id,
        active_user_role=next_role,
        story_ledger=story_ledger_text(next_state),
        scene_state=next_scene,
        story_state=next_state,
    )
    narrative["chapter_entry_checkpoint_id"] = entry_id

    update_run_snapshot(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        active_user_role=next_role,
        story_ledger=story_ledger_text(next_state),
        scene_state=next_scene,
        story_state=next_state,
    )
    st.rerun()

def apply_pending_auto_transition(persistence: dict | None) -> bool:
    """Aplica o próximo microcapítulo sem botão visível."""
    narrative = st.session_state.story_state.setdefault("narrative", {})
    next_chapter_id = str(narrative.get("pending_auto_chapter", "") or "").strip()
    if not next_chapter_id:
        return False

    chapter = get_chapter(next_chapter_id)
    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)
    handoff = (
        _handoff_from_record(st.session_state.turn_records[-1])
        if st.session_state.turn_records
        else {}
    )

    narrative["chapter_id"] = next_chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    # A sequência continua visível; só o contexto enviado à LLM recomeça aqui.
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = handoff

    st.session_state.scene_state = _scene_for_chapter_transition(
        chapter,
        st.session_state.scene_state,
    )

    next_role = str(
        st.session_state.scene_state.get("user_role", "JANIO") or "JANIO"
    ).upper()
    if next_role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
        next_role = "JANIO"
    st.session_state.active_user_role = next_role

    # Fronteira real de prompt: limpa contexto da LLM, preserva histórico visual.
    st.session_state.messages = []

    if persistence and st.session_state.run_id:
        update_run_snapshot(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            active_user_role=st.session_state.active_user_role,
            story_ledger=story_ledger_text(st.session_state.story_state),
            scene_state=st.session_state.scene_state,
            story_state=st.session_state.story_state,
        )

    return True


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
    fallback_model: str | None,
) -> dict:
    """Fallback para snapshots antigos sem reconstrução narrativa por LLM."""
    rows = load_run_interactions(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=run_id,
    )
    rows = [
        row for row in rows
        if int(row.get("seq", 0) or 0) < int(before_seq)
    ]

    story_state = new_state()
    scene_state = deepcopy(INITIAL_SCENE)
    messages: list[dict[str, str]] = []
    active_role = "JANIO"

    for row in rows:
        role = str(row.get("user_role", "JANIO") or "JANIO").upper()
        if role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
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
            physical_canon=PHYSICAL_CANON,
            story_ledger=story_ledger_text(story_state),
            current_status=current_status_text(story_state),
            current_scene=scene_state,
            user_role=role,
            recent_messages=messages,
            scene_direction=direction,
            user_spoke=user_spoke,
            chapter_text=chapter_prompt(
                story_state.get("narrative", {}).get(
                    "chapter_id",
                    "confissao_inicial",
                )
            ),
        )

        if mary_text:
            messages.append({"role": "assistant", "content": mary_text})

        active_role = role

    return {
        "active_user_role": active_role,
        "story_ledger": story_ledger_text(story_state),
        "scene_state": scene_state,
        "story_state": story_state,
    }


for key, default in {
    "messages": [],
    "story_state": new_state(),
    "scene_state": dict(INITIAL_SCENE),
    "turn_records": [],
    "run_id": "",
    "active_user_role": "JANIO",
    "persistence_loaded": False,
    "persistence_error": "",
    "spreadsheet_url": "",
    "rollback_notice": "",
    "rollback_retry_text": "",
    "run_last_seq": 0,
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
            st.session_state.scene_state = saved["scene_state"] or dict(INITIAL_SCENE)
            st.session_state.story_state = migrate_state(saved["story_state"])
            st.session_state.run_last_seq = int(saved.get("last_seq", 0) or 0)

            chapter_start_seq = int(
                st.session_state.story_state.get("narrative", {}).get(
                    "chapter_start_seq",
                    1,
                )
                or 1
            )
            st.session_state.turn_records = [
                record
                for record in saved["turn_records"]
                if int(record.get("seq", 0) or 0) >= chapter_start_seq
            ]
            prompt_start_seq = int(
                st.session_state.story_state.get("narrative", {}).get(
                    "prompt_start_seq",
                    chapter_start_seq,
                )
                or chapter_start_seq
            )
            prompt_records = [
                record
                for record in saved["turn_records"]
                if int(record.get("seq", 0) or 0) >= prompt_start_seq
            ]
            st.session_state.messages = _messages_from_records(prompt_records)
        else:
            st.session_state.run_id = create_run(
                service_account_info=persistence["service_account_info"],
                spreadsheet_id=info["spreadsheet_id"],
                spreadsheet_title=persistence["spreadsheet_title"],
                owner_email=persistence["owner_email"],
                player_id=persistence["player_id"],
                active_user_role=st.session_state.active_user_role,
                story_ledger=story_ledger_text(st.session_state.story_state),
                scene_state=st.session_state.scene_state,
                story_state=st.session_state.story_state,
                archive_previous=False,
            )
            st.session_state.run_last_seq = 0

        st.session_state.persistence_loaded = True
        st.session_state.persistence_error = ""
    except Exception as exc:
        st.session_state.persistence_loaded = True
        st.session_state.persistence_error = str(exc)


st.title("Mary Core 2")
st.caption("Novela interativa por capítulos, com contexto renovado a cada decisão.")
st.caption(f"Build: `{BUILD_ID}`")

current_chapter = get_chapter(_chapter_id())
st.caption(f"Capítulo atual: **{current_chapter.get('title', _chapter_id())}**")

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

    allowed_roles = list(
        current_chapter.get("allowed_roles", ["JANIO"]) or ["JANIO"]
    )
    temporary_available = bool(
        temporary_character.get("active")
        and temporary_character.get("user_can_play")
        and str(temporary_character.get("name", "") or "").strip()
    )

    role_options = []
    for allowed_role in allowed_roles:
        role_name = str(allowed_role).upper()
        if role_name == "JANIO":
            role_options.append("JANIO")
        elif role_name == "PERSONAGEM_DA_CENA" and temporary_available:
            role_options.append("PERSONAGEM_DA_CENA")

    if not role_options:
        role_options = ["JANIO"]

    current_role = st.session_state.active_user_role
    if current_role not in role_options:
        current_role = role_options[0]

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
                    story_ledger=story_ledger_text(new_state()),
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
            st.markdown(f"[Abrir planilha da história]({st.session_state.spreadsheet_url})")
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
                    "Ledger, cena e estado voltam ao ponto imediatamente anterior."
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
                                "story_ledger_before",
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
                        st.session_state.scene_state = (
                            saved["scene_state"] or dict(INITIAL_SCENE)
                        )
                        st.session_state.story_state = migrate_state(
                            saved["story_state"]
                        )
                        st.session_state.run_last_seq = int(
                            saved.get("last_seq", 0) or 0
                        )
                        chapter_start_seq = int(
                            st.session_state.story_state.get("narrative", {}).get(
                                "chapter_start_seq",
                                1,
                            )
                            or 1
                        )
                        st.session_state.turn_records = [
                            record
                            for record in saved["turn_records"]
                            if int(record.get("seq", 0) or 0) >= chapter_start_seq
                        ]
                        prompt_start_seq = int(
                            st.session_state.story_state.get("narrative", {}).get(
                                "prompt_start_seq",
                                chapter_start_seq,
                            )
                            or chapter_start_seq
                        )
                        prompt_records = [
                            record
                            for record in saved["turn_records"]
                            if int(record.get("seq", 0) or 0) >= prompt_start_seq
                        ]
                        st.session_state.messages = _messages_from_records(
                            prompt_records
                        )
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

    with st.expander("Story ledger"):
        st.text(story_ledger_text(st.session_state.story_state))

    with st.expander("Status atual"):
        st.json(st.session_state.story_state.get("current_status", {}))

    with st.expander("Estado do capítulo"):
        st.json(st.session_state.story_state.get("narrative", {}))


def generate_model_chapter_opening(
    *,
    model: str,
    temperature: float,
    persistence: dict | None,
) -> None:
    """Gera a primeira fala real de Mary após uma transição manual de capítulo."""
    narrative = st.session_state.story_state.setdefault("narrative", {})
    chapter = get_chapter(_chapter_id())

    if not narrative.get("chapter_opening_pending"):
        return
    if not bool(chapter.get("model_opening", False)):
        return
    if st.session_state.turn_records:
        return

    api_key = str(st.secrets["OPENROUTER_API_KEY"]).strip()
    fallback = str(st.secrets.get("MARY_FALLBACK_MODEL", "")).strip() or None
    director_model = str(st.secrets.get("MARY_DIRECTOR_MODEL", model)).strip() or model

    user_role = str(st.session_state.active_user_role or "JANIO").upper()
    pre_turn_snapshot = {
        "active_user_role": user_role,
        "story_ledger": story_ledger_text(st.session_state.story_state),
        "scene_state": deepcopy(st.session_state.scene_state),
        "story_state": deepcopy(st.session_state.story_state),
    }

    opening_phase = chapter_phase(_chapter_id(), 1)
    opening_phase_id = str(opening_phase.get("id", "") or "").strip()
    opening_phase_goal = str(opening_phase.get("goal", "") or "").strip()
    opening_chapter_prompt = chapter_prompt(_chapter_id(), turn_number=1)

    opening_scene = deepcopy(st.session_state.scene_state)
    opening_scene["chapter_turn_current"] = 1
    opening_scene["chapter_phase"] = opening_phase_id
    opening_scene["chapter_phase_goal"] = opening_phase_goal
    if opening_phase_id:
        opening_scene["arc_phase"] = opening_phase_id
        opening_scene["mary_immediate_goal"] = ""

    scene = direct_scene(
        api_key=api_key,
        model=director_model,
        fallback_model=fallback,
        physical_canon=PHYSICAL_CANON,
        story_ledger=story_ledger_text(st.session_state.story_state),
        current_status=current_status_text(st.session_state.story_state),
        current_scene=opening_scene,
        user_role=user_role,
        recent_messages=[],
        scene_direction="",
        user_spoke=False,
        chapter_text=opening_chapter_prompt,
    )
    director_audit = scene.pop("_director_audit", {})

    opening_caption = str(chapter.get("opening_caption", "") or "").strip()
    if opening_caption:
        scene["show_caption"] = True
        scene["scene_caption"] = opening_caption

    system_prompt = build_system_prompt(
        physical_canon=PHYSICAL_CANON,
        story_ledger=story_ledger_text(st.session_state.story_state),
        current_status=current_status_text(st.session_state.story_state),
        chapter_text=opening_chapter_prompt,
        scene_text=json.dumps(scene, ensure_ascii=False),
        user_role=user_role,
        handoff_text=_handoff_text(st.session_state.story_state),
    )

    opening_instruction = {
        "role": "system",
        "content": (
            "INÍCIO AUTOMÁTICO DO CAPÍTULO: esta é a primeira fala real de Mary "
            "neste capítulo. Inicie a cena conforme CAPÍTULO ATUAL e CENA ATUAL. "
            "Não espere uma fala do usuário. Gere a resposta no formato [FALA] e depois [PENSAMENTO]."
        ),
    }

    raw_answer = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback,
        messages=[
            {"role": "system", "content": system_prompt},
            opening_instruction,
        ],
        temperature=temperature,
    )
    mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
    narration_leak = looks_like_action_narration(mary_speech_raw)
    answer = sanitize_mary_output(mary_speech_raw)

    if not answer or narration_leak:
        raw_answer = chat(
            api_key=api_key,
            model=model,
            fallback_model=fallback,
            messages=[
                {"role": "system", "content": system_prompt},
                opening_instruction,
                {
                    "role": "system",
                    "content": (
                        "CORREÇÃO DE FORMATO: use exatamente [FALA] e depois [PENSAMENTO]. "
                        "[FALA] deve conter somente palavras que Mary diria em voz alta, "
                        "[PENSAMENTO] deve ser uma frase curta em primeira pessoa escrita depois da fala, "
                        "também em primeira pessoa. Gestos, aparência, postura e movimentos "
                        "pertencem ao Diretor. Use sensação corporal somente quando Mary "
                        "realmente a verbalizaria numa conversa."
                    ),
                },
            ],
            temperature=max(0.2, min(float(temperature), 0.8)),
        )
        mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
        narration_leak = looks_like_action_narration(mary_speech_raw)
        answer = sanitize_mary_output(mary_speech_raw)

    if not answer or narration_leak:
        raise OpenRouterError(
            "O modelo não produziu uma abertura verbal limpa para o novo capítulo."
        )

    st.session_state.scene_state = scene
    st.session_state.messages = [{"role": "assistant", "content": answer}]
    narrative["chapter_opening_pending"] = False

    caption = scene.get("scene_caption", "") if scene.get("show_caption") else ""
    turn_record = {
        "seq": 0,
        "caption": caption,
        "direction": "",
        "mary_action": str(scene.get("mary_action", "") or "").strip(),
        "hook_resolution": str(scene.get("hook_resolution", "") or "").strip(),
        "mary_intent": mary_intent,
        "user_role": user_role,
        "user_text": "",
        "mary_text": answer,
        "branch_id": str(narrative.get("branch_id", "main") or "main"),
        "chapter_instance_id": str(narrative.get("chapter_instance_id", "") or ""),
        "chapter_id": _chapter_id(),
        "chapter_turn": 0,
    }
    st.session_state.turn_records = [turn_record]

    if persistence:
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
                story_ledger=story_ledger_text(st.session_state.story_state),
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
            story_ledger=story_ledger_text(st.session_state.story_state),
            scene_state=st.session_state.scene_state,
            story_state=st.session_state.story_state,
            turn_record=turn_record,
            pre_turn_snapshot=pre_turn_snapshot,
        )
        turn_record["seq"] = saved_seq
        st.session_state.run_last_seq = saved_seq
        save_director_audit(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=info["spreadsheet_id"],
            spreadsheet_title=persistence["spreadsheet_title"],
            owner_email=persistence["owner_email"],
            run_id=st.session_state.run_id,
            seq=saved_seq,
            chapter_id=_chapter_id(),
            user_role=user_role,
            user_text="",
            scene_direction="",
            audit=director_audit,
            main_model=model,
            mary_text=answer,
        )


try:
    generate_model_chapter_opening(
        model=model,
        temperature=temperature,
        persistence=persistence,
    )
except KeyError:
    st.error("OPENROUTER_API_KEY não encontrada em st.secrets.")
except OpenRouterError as exc:
    st.error(f"Erro OpenRouter ao abrir capítulo: {exc}")
except PersistenceError as exc:
    st.error(f"Erro de persistência ao abrir capítulo: {exc}")
except Exception as exc:
    st.error(f"Erro inesperado ao abrir capítulo: {exc}")


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
        if record.get("mary_intent"):
            st.caption("💭 " + str(record["mary_intent"]))
        st.markdown(_mary_display_text(record["mary_text"]))


if not st.session_state.turn_records:
    opening_caption = str(current_chapter.get("opening_caption", "") or "").strip()
    opening_mary = str(current_chapter.get("opening_mary", "") or "").strip()

    if opening_caption:
        st.info(opening_caption)
    elif _chapter_id() == "confissao_inicial":
        st.info(
            "Na casa do casal, pouco depois da confissão, "
            "Mary tenta impedir que Janio encerre a conversa."
        )

    if opening_mary:
        with st.chat_message("assistant"):
            st.markdown(opening_mary)
    elif _chapter_id() == "confissao_inicial":
        with st.chat_message("assistant"):
            st.markdown("Janio... olha pra mim. Só... não vai embora ainda.")


chapter_id = _chapter_id()
chapter_turns = _chapter_turns()
if chapter_ready_for_choice(chapter_id, chapter_turns):
    available_choices = chapter_choices(chapter_id)
    st.divider()
    st.subheader("Decisão")
    st.caption("Escolha o rumo do próximo capítulo.")

    choice_columns = st.columns(len(available_choices))
    for column, choice in zip(choice_columns, available_choices):
        with column:
            if st.button(
                str(choice.get("label", "Escolher")),
                key=f"chapter_choice_{chapter_id}_{choice.get('id', '')}",
                use_container_width=True,
            ):
                activate_chapter(
                    next_chapter_id=str(choice.get("next_chapter", "") or ""),
                    choice_id=str(choice.get("id", "") or ""),
                    persistence=persistence,
                )


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

        # Um micropasso concluído troca de prompt antes de processar a próxima fala.
        apply_pending_auto_transition(persistence)

        previous_scene_role = str(
            st.session_state.scene_state.get(
                "user_role",
                st.session_state.active_user_role,
            )
            or "JANIO"
        ).upper()
        pre_turn_snapshot = {
            "active_user_role": previous_scene_role,
            "story_ledger": story_ledger_text(st.session_state.story_state),
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

        current_turn_number = _chapter_turns() + 1
        chapter_config = get_chapter(_chapter_id())
        current_phase = chapter_phase(_chapter_id(), current_turn_number)
        current_phase_id = str(current_phase.get("id", "") or "").strip()
        current_phase_goal = str(current_phase.get("goal", "") or "").strip()
        previous_phase_id = str(
            st.session_state.scene_state.get("chapter_phase", "") or ""
        ).strip()
        phase_changed = bool(current_phase_id) and current_phase_id != previous_phase_id

        narrative_state = st.session_state.story_state.setdefault("narrative", {})
        phase_context_mode = str(
            chapter_config.get("phase_context", "") or ""
        ).strip().lower()

        if phase_changed and phase_context_mode == "phase":
            # A fase nova começa com a fala atual do usuário, não com exemplos
            # linguísticos/comportamentais das fases encerradas.
            narrative_state["phase_start_message_index"] = len(messages_before_turn)
            narrative_state["active_phase_id"] = current_phase_id

        phase_messages = st.session_state.messages
        if current_phase_id and phase_context_mode == "phase":
            start_index = int(
                narrative_state.get("phase_start_message_index", 0) or 0
            )
            start_index = max(0, min(start_index, len(st.session_state.messages)))
            phase_messages = st.session_state.messages[start_index:]

        scene_for_director = deepcopy(st.session_state.scene_state)
        scene_for_director["chapter_turn_current"] = current_turn_number
        scene_for_director["chapter_phase"] = current_phase_id
        scene_for_director["chapter_phase_goal"] = current_phase_goal

        if current_phase_id:
            # Em capítulos com contador, a fase é estado determinístico do runtime.
            scene_for_director["arc_phase"] = current_phase_id

        if phase_changed:
            # Remove resíduos transitórios da fase anterior.
            scene_for_director["mary_immediate_goal"] = ""
            scene_for_director["mary_action"] = ""
            scene_for_director["event"] = ""
            scene_for_director["return_anchor"] = ""

        current_chapter_prompt = chapter_prompt(
            _chapter_id(),
            turn_number=current_turn_number,
        )

        scene = direct_scene(
            api_key=api_key,
            model=director_model,
            fallback_model=fallback,
            physical_canon=PHYSICAL_CANON,
            story_ledger=story_ledger_text(st.session_state.story_state),
            current_status=current_status_text(st.session_state.story_state),
            current_scene=scene_for_director,
            user_role=user_role,
            recent_messages=phase_messages,
            scene_direction=scene_direction,
            user_spoke=user_spoke,
            chapter_text=current_chapter_prompt,
            conditional_transition=(
                str(get_chapter(_chapter_id()).get("transition", "")) == "auto_condition"
            ),
            advance_when=str(
                get_chapter(_chapter_id()).get("advance_when", "") or ""
            ),
        )
        director_audit = scene.pop("_director_audit", {})
        scene["chapter_turn_current"] = current_turn_number
        scene["chapter_phase"] = current_phase_id
        scene["chapter_phase_goal"] = current_phase_goal
        if current_phase_id:
            # Em capítulos com microprompt, o runtime já define a direção
            # psicológica. O Diretor permanece responsável pela cena física.
            scene["arc_phase"] = current_phase_id
            scene["mary_immediate_goal"] = ""

        # Eventos de entrada pertencem ao mundo, não a Mary nem ao personagem do usuário.
        # São exibidos uma única vez, quando uma nova fase começa.
        if phase_changed:
            phase_entry_caption = str(
                current_phase.get("entry_caption", "") or ""
            ).strip()
            if phase_entry_caption:
                scene["show_caption"] = True
                scene["scene_caption"] = phase_entry_caption

        narrative_for_opening = st.session_state.story_state.get("narrative", {})
        if narrative_for_opening.get("chapter_opening_pending"):
            opening_caption = str(
                get_chapter(_chapter_id()).get("opening_caption", "") or ""
            ).strip()
            if opening_caption:
                scene["show_caption"] = True
                scene["scene_caption"] = opening_caption

        scene_text = json.dumps(scene, ensure_ascii=False)
        system_prompt = build_system_prompt(
            physical_canon=PHYSICAL_CANON,
            story_ledger=story_ledger_text(st.session_state.story_state),
            current_status=current_status_text(st.session_state.story_state),
            chapter_text=current_chapter_prompt,
            scene_text=scene_text,
            user_role=user_role,
            handoff_text=_handoff_text(st.session_state.story_state),
        )

        llm_messages = [
            {"role": "system", "content": system_prompt},
            *phase_messages[-24:],
        ]

        try:
            raw_answer = chat(
                api_key=api_key,
                model=model,
                fallback_model=fallback,
                messages=llm_messages,
                temperature=temperature,
            )
            mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
            narration_leak = looks_like_action_narration(mary_speech_raw)
            answer = sanitize_mary_output(mary_speech_raw)

            if not answer or narration_leak:
                retry_messages = [
                    *llm_messages,
                    {
                        "role": "system",
                        "content": (
                            "CORREÇÃO DE FORMATO: use exatamente [FALA] e depois [PENSAMENTO]. "
                            "[FALA] contém somente o que Mary diz em voz alta. "
                            "[PENSAMENTO] é uma frase curta em primeira pessoa escrita somente "
                            "depois da fala; não planeje nem explique a fala. Não escreva narração externa, "
                            "rubricas, metáforas literárias ou ações como descrição. "
                            "As ações físicas pertencem exclusivamente ao Diretor."
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
                mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
                narration_leak = looks_like_action_narration(mary_speech_raw)
                answer = sanitize_mary_output(mary_speech_raw)

            if not answer or narration_leak:
                raise OpenRouterError(
                    "O modelo não produziu fala verbal limpa de Mary após duas tentativas."
                )
        except Exception:
            # Turno atômico: nada da tentativa incompleta fica na sessão.
            st.session_state.scene_state = deepcopy(
                pre_turn_snapshot["scene_state"]
            )
            st.session_state.story_state = deepcopy(
                pre_turn_snapshot["story_state"]
            )
            st.session_state.active_user_role = pre_turn_snapshot[
                "active_user_role"
            ]
            st.session_state.messages = messages_before_turn
            raise

        # Só confirma a cena depois que Mary respondeu de fato.
        st.session_state.scene_state = scene
        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        narrative = st.session_state.story_state.setdefault("narrative", {})
        narrative["chapter_turns"] = int(
            narrative.get("chapter_turns", 0) or 0
        ) + 1
        if narrative.get("chapter_opening_pending"):
            narrative["chapter_opening_pending"] = False

        active_chapter = get_chapter(_chapter_id())
        if (
            str(active_chapter.get("transition", "")) == "auto_condition"
            and bool(scene.get("microstep_complete", False))
        ):
            # O micropasso pode durar quantos turnos a cena exigir.
            # A troca ocorre somente após um evento concreto reconhecido pelo Diretor.
            narrative["pending_auto_chapter"] = str(
                active_chapter.get("auto_next", "") or ""
            ).strip()

        caption = scene.get("scene_caption", "") if scene.get("show_caption") else ""

        turn_record = {
            "seq": 0,
            "caption": caption,
            "direction": scene_direction,
            "mary_action": str(scene.get("mary_action", "") or "").strip(),
            "hook_resolution": str(scene.get("hook_resolution", "") or "").strip(),
            "mary_intent": mary_intent,
            "user_role": user_role,
            "user_text": dialogue_text,
            "mary_text": answer,
            "branch_id": str(narrative.get("branch_id", "main") or "main"),
            "chapter_instance_id": str(narrative.get("chapter_instance_id", "") or ""),
            "chapter_id": _chapter_id(),
            "chapter_turn": int(narrative.get("chapter_turns", 0) or 0),
        }
        st.session_state.turn_records.append(turn_record)

        # O ledger não é atualizado pelo LLM. Só decisões estruturais de capítulo o alteram.

        # Persiste o turno com ledger/status estruturais atuais.
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
                        story_ledger=story_ledger_text(st.session_state.story_state),
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
                    story_ledger=story_ledger_text(st.session_state.story_state),
                    scene_state=st.session_state.scene_state,
                    story_state=st.session_state.story_state,
                    turn_record=turn_record,
                    pre_turn_snapshot=pre_turn_snapshot,
                )
                turn_record["seq"] = saved_seq
                st.session_state.run_last_seq = saved_seq
                save_director_audit(
                    service_account_info=persistence["service_account_info"],
                    spreadsheet_id=info["spreadsheet_id"],
                    spreadsheet_title=persistence["spreadsheet_title"],
                    owner_email=persistence["owner_email"],
                    run_id=st.session_state.run_id,
                    seq=saved_seq,
                    chapter_id=_chapter_id(),
                    user_role=user_role,
                    user_text=dialogue_text,
                    scene_direction=scene_direction,
                    audit=director_audit,
                    main_model=model,
                    mary_text=answer,
                )
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
