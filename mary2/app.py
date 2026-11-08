from __future__ import annotations

HUMANIZER_INTERPRETATIVO = """
HUMANIZAÇÃO — QUALIDADE EXPRESSIVA
Os três guias e o estilo da linha definem o conteúdo, as emoções e a intensidade;
este contrato aprimora apenas a expressão, sem mudar a autoria.
[AÇÃO]: linguagem concreta e proporcional ao acontecimento; evite microgestos,
clima e sensações de preenchimento. Preserve os movimentos relevantes da cena.
[FALA]: português brasileiro vivo, situado e espontâneo, sem discurso explicativo,
frases feitas ou perguntas em série quando a conversa pede espaço para resposta.
[PENSAMENTO]: voz interior própria, íntima e natural; expresse as emoções,
motivações e conflitos que emergirem da conversa e do PENSAMENTO-GUIA, sem
impor categorias emocionais fixas nem converter pensamento em ação obrigatória.
Se mostrado antes do diálogo, expresse apenas o que Mary sente ou sabe naquele
instante; não resuma antecipadamente as falas, reações e decisões da cena.
Evite que ação, fala e pensamento repitam a mesma informação por obrigação.
Não fixe comprimento nem intensidade: acompanhe o roteiro e a conversa real.
"""


import html
import json
import logging
import re
import sys
from pathlib import Path
from copy import deepcopy

# Módulos homônimos existem na raiz (app legado) e em mary2/.
# Priorizar mary2/ para que director, openrouter_client e os demais módulos
# deste motor não sejam resolvidos acidentalmente para a versão legada.
_MARY2_DIR = str(Path(__file__).resolve().parent)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)
if _MARY2_DIR in sys.path:
    sys.path.remove(_MARY2_DIR)
sys.path.insert(0, _MARY2_DIR)

import streamlit as st

from chapters import (
    apply_choice_to_story,
    chapter_choices,
    chapter_phase,
    chapter_prompt,
    chapter_ready_for_choice,
    find_choice,
    get_chapter as get_legacy_chapter,
)
from director import direct_scene
from direct_semantic_director import validate_direct_semantic_turn
from conversation_state import analyze_mary_move, normalize_conversation_state
from input_router import parse_user_input
from direct_script import (
    advance_emitted_automatic_line,
    build_direct_chapter,
    build_direct_writer_prompt,
    current_direct_row,
    direct_chapter_id,
    direct_script_id_from_chapter_id,
    direct_line_correction_prompt,
    direct_script_ready_for_choice,
    ensure_direct_state,
    extract_direct_character_name,
    hurt_loop_max_interactions,
    is_automatic_direct_row,
    is_blocked_direct_row,
    is_direct_thought_disabled,
    load_direct_script_catalog,
    load_direct_info_board,
    load_direct_script_rows,
    mark_direct_line_emitted,
    next_direct_script,
    record_direct_line_turn,
    register_direct_user_reply,
)
from hybrid_script import (
    build_carona_prompt,
    carona_ready_for_choice,
    closing_convergence_prompt,
    consume_breath,
    ensure_carona_state,
    load_sheet_script,
    mark_carona_line_emitted,
    register_user_reply,
    select_carona_line,
)
from block_script import (
    apply_block_turn,
    block_ready_for_choice,
    build_block_prompt,
    current_block_row,
    ensure_block_state,
    evaluate_block_dependency,
    load_block_rows,
)
from funnel_script import (
    apply_funnel_evaluation,
    build_funnel_prompt,
    compact_context_messages,
    correction_prompt,
    current_funnel_row,
    ensure_funnel_state,
    evaluate_funnel_turn,
    funnel_ready_for_choice,
    load_funnel_rows,
    pending_markers,
    required_markers,
)
from openrouter_client import OpenRouterError, chat
from output_filter import looks_like_action_narration, parse_mary_response, parse_mary_components, sanitize_mary_output, format_dialogue_paragraphs
from user_understanding_audit import (
    analyze_user_understanding,
    save_user_understanding_audit,
)
from episodic_memory_shadow import select_episodic_candidates, describe_episode_selection
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
    save_block_audit,
    save_direct_script_audit,
    save_director_validation_audit,
    save_checkpoint,
    save_director_audit,
    save_funnel_audit,
    save_funnel_rejection,
    save_model_audit,
    save_episodic_memory_audit,
    save_turn,
    update_run_snapshot,
)
from prompts import build_system_prompt
from state import current_status_text, migrate_state, new_state, story_ledger_text
from story_bible import PHYSICAL_CANON


st.set_page_config(page_title="Mary Core 2", page_icon="🖤", layout="centered")

_LOG = logging.getLogger(__name__)

BUILD_ID = "2026-10-09-sheet-runtime-v8.5-full-user-turn"


def _runtime_get_chapter(chapter_id: str) -> dict:
    """Resolve capítulos legados ou capítulos diretos descobertos na planilha."""
    script_id = direct_script_id_from_chapter_id(chapter_id)
    if script_id:
        return build_direct_chapter(script_id)

    chapter = get_legacy_chapter(chapter_id)
    # Compatibilidade temporária enquanto os capítulos anteriores são recompilados:
    # a Carona já usa o novo ID autoral Nome+índice presente na MINHA_SUGESTAO.
    if str(chapter_id) == "carona_camburi":
        chapter["script_name"] = "Carona4"
    return chapter



DEFAULT_MODELS = [
    "google/gemini-3-flash-preview",
    "google/gemini-2.5-flash-lite",
    "google/gemma-4-31b-it",
    "Outro...",
]

# O primeiro capítulo é descoberto na planilha, nunca fixado no código.
# Cache curto evita leituras repetidas a cada rerun do Streamlit.
@st.cache_data(ttl=60, show_spinner=False)
def _first_sheet_script_id() -> str:
    try:
        credentials = (st.secrets.get("GOOGLE_CREDS_JSON") or st.secrets.get("gcp_service_account") or st.secrets.get("GOOGLE_SERVICE_ACCOUNT"))
        if isinstance(credentials, str):
            credentials = json.loads(credentials)
        credentials = dict(credentials)
        if isinstance(credentials.get("private_key"), str):
            credentials["private_key"] = credentials["private_key"].replace("\\n", "\n")
        spreadsheet_id = str(st.secrets.get("MARY_SHEETS_ID", "") or "").strip()
        catalog = load_direct_script_catalog(
            service_account_info=credentials,
            spreadsheet_id=spreadsheet_id,
            worksheet_name="MINHA_SUGESTAO",
        )
        executable = [row for row in catalog if int(row.get("executable_row_count", 0) or 0) > 0]
        return str(executable[0]["script_id"]) if executable else ""
    except Exception as exc:
        _LOG.warning("Não foi possível descobrir capítulo inicial: %s", exc)
        return ""


def _initial_chapter_id() -> str:
    script_id = _first_sheet_script_id()
    return direct_chapter_id(script_id) if script_id else "sheet:"


_base_new_state = new_state


def new_state() -> dict:
    state = _base_new_state()
    chapter_id = _initial_chapter_id()
    state["narrative"]["chapter_id"] = chapter_id
    state["narrative"]["chapter_instance_id"] = (
        f"sheet_{_first_sheet_script_id()}_001" if _first_sheet_script_id() else ""
    )
    return state


def _initial_scene() -> dict:
    script_id = _first_sheet_script_id()
    return deepcopy(build_direct_chapter(script_id).get("initial_scene", {})) if script_id else {}


INITIAL_SCENE = _initial_scene()


def _mary_display_text(text: str) -> str:
    """Formata falas por personagem apenas na interface, sem tocar no histórico."""
    return format_dialogue_paragraphs(text)


def _render_scene_action(text: str) -> None:
    value = str(text or "").strip()
    if not value:
        return
    st.markdown(
        (
            '<div style="margin:0.45rem 0 0.8rem; padding:0.68rem 0.85rem; '
            'border-radius:0.7rem; background:rgba(127,127,127,0.08); '
            'font-weight:650; line-height:1.5;">'
            + html.escape(value)
            + "</div>"
        ),
        unsafe_allow_html=True,
    )



def _direct_auto_retry_key(chapter_id: str, instance_id: str, order: int) -> str:
    """Isola tentativas falhas por instância e linha do roteiro."""
    return f"auto_retry_required_{chapter_id}_{instance_id}_{order}"


def _parse_direct_flexible_response(
    raw: str, script_mode: str, *, thought_disabled: bool = False
) -> tuple[str, str]:
    """No roteiro direto, a fala e o pensamento sao opcionais; a acao e independente."""
    if script_mode == "direct_sheet":
        parts = parse_mary_components(raw)
        return ("" if thought_disabled else parts["thought"]), parts["speech"]
    return parse_mary_response(raw)


def _render_mary_thought(text: str) -> None:
    value = str(text or "").strip()
    if not value:
        return
    st.markdown(
        (
            '<div style="margin:0.1rem 0 0.8rem; padding:0.78rem 0.95rem; '
            'border-radius:0.9rem; background:rgba(127,127,127,0.07); '
            'font-size:1rem; line-height:1.55;">'
            '<span style="font-size:1.08rem; margin-right:0.35rem;">💭</span>'
            '<span style="font-style:italic; opacity:0.92;">'
            + html.escape(value)
            + "</span></div>"
        ),
        unsafe_allow_html=True,
    )


def reset_local_story() -> None:
    st.session_state.messages = []
    st.session_state.story_state = new_state()
    st.session_state.scene_state = deepcopy(INITIAL_SCENE)
    st.session_state.turn_records = []
    st.session_state.active_user_role = "PERSONAGEM_DA_CENA"
    st.session_state.run_last_seq = 0
    st.session_state.route_checkpoints = []
    st.session_state.route_checkpoints_loaded_for_run = ""


def _messages_from_records(records: list[dict]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for record in records:
        direction = str(record.get("direction", "") or "").strip()
        dialogue = str(record.get("user_text", "") or "").strip()
        if direction or dialogue:
            parts = [f"[PAPEL={record.get('user_role', 'JANIO')}]"]
            if direction:
                parts.append(f"[DIREÇÃO/ENCENAÇÃO] {direction}")
            if dialogue:
                parts.append(f"[FALA] {dialogue}")
            messages.append({
                "role": "user",
                "content": "\n".join(parts),
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

    if bool(chapter.get("inherit_character", False)):
        previous_character = deepcopy(
            (previous_scene or {}).get("temporary_character", {}) or {}
        )
        previous_name = str(previous_character.get("name", "") or "").strip()
        if (
            previous_character.get("active")
            and previous_name
            and previous_name.lower() not in {"personal", "personagem", "personagem_da_cena", "personagem da cena"}
        ):
            initial["temporary_character"] = previous_character
            present = list(initial.get("present_characters", []) or [])
            initial["present_characters"] = [
                previous_name if str(item).upper() == "PERSONAGEM_DA_CENA" else item
                for item in present
            ]

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
    return str(narrative.get("chapter_id") or _initial_chapter_id())


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
        st.session_state.route_checkpoints_loaded_for_run = ""

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
    narrative["choice_ready"] = False
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    chapter = _runtime_get_chapter(next_chapter_id)
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




def activate_direct_sheet_chapter(
    *,
    script_id: str,
    persistence: dict | None,
) -> None:
    """Avança linearmente para um roteiro Nome+índice descoberto na MINHA_SUGESTAO."""
    chapter = build_direct_chapter(script_id)
    next_chapter_id = direct_chapter_id(script_id)
    if not next_chapter_id:
        raise ValueError("Roteiro direto inválido para transição.")

    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)
    previous_scene = deepcopy(st.session_state.scene_state)
    next_state = deepcopy(st.session_state.story_state)
    narrative = next_state.setdefault("narrative", {})
    branch_id = str(narrative.get("branch_id", "main") or "main")
    instance_id = new_chapter_instance_id(next_chapter_id)

    handoff = (
        _handoff_from_record(st.session_state.turn_records[-1])
        if st.session_state.turn_records
        else {}
    )

    narrative["chapter_id"] = next_chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    narrative["chapter_start_seq"] = last_seq + 1
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["last_choice_id"] = f"continue:{script_id}"
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = handoff
    narrative["chapter_instance_id"] = instance_id
    narrative["chapter_entry_checkpoint_id"] = ""
    narrative["choice_ready"] = False
    narrative.pop("direct_script", None)
    narrative.pop("direct_conversation_state", None)
    narrative.pop("direct_recent_user_facts", None)
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    next_scene = _scene_for_chapter_transition(chapter, previous_scene)
    next_role = str(
        next_scene.get("user_role", st.session_state.active_user_role)
        or st.session_state.active_user_role
        or "JANIO"
    ).upper()
    if next_role not in {"JANIO", "PERSONAGEM_DA_CENA"}:
        next_role = "JANIO"

    st.session_state.story_state = next_state
    st.session_state.scene_state = next_scene
    st.session_state.active_user_role = next_role
    st.session_state.messages = []
    st.session_state.turn_records = []

    if persistence and st.session_state.run_id:
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
    narrative["choice_ready"] = False
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = {}
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    restored_scene = deepcopy(entry_scene)
    restored_role = entry_role if entry_role in {"JANIO", "PERSONAGEM_DA_CENA"} else "JANIO"

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
        active_user_role=restored_role,
        story_ledger=story_ledger_text(restored),
        scene_state=restored_scene,
        story_state=restored,
    )
    narrative["chapter_entry_checkpoint_id"] = new_entry_checkpoint_id

    update_run_snapshot(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        spreadsheet_title=persistence["spreadsheet_title"],
        owner_email=persistence["owner_email"],
        run_id=st.session_state.run_id,
        active_user_role=restored_role,
        story_ledger=story_ledger_text(restored),
        scene_state=restored_scene,
        story_state=restored,
    )
    # A failed write leaves the current conversation available for retry.
    st.session_state.story_state = restored
    st.session_state.scene_state = restored_scene
    st.session_state.active_user_role = restored_role
    st.session_state.messages = []
    st.session_state.turn_records = []
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
    narrative["choice_ready"] = False
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

    chapter = _runtime_get_chapter(next_chapter_id)
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

    chapter = _runtime_get_chapter(next_chapter_id)
    last_seq = int(st.session_state.get("run_last_seq", 0) or 0)
    handoff = (
        _handoff_from_record(st.session_state.turn_records[-1])
        if st.session_state.turn_records
        else {}
    )

    branch_id = str(narrative.get("branch_id", "main") or "main")
    instance_id = new_chapter_instance_id(next_chapter_id)

    narrative["chapter_id"] = next_chapter_id
    narrative["chapter_turns"] = 0
    narrative["chapter_opening_pending"] = True
    narrative["prompt_start_seq"] = last_seq + 1
    narrative["pending_auto_chapter"] = ""
    narrative["handoff"] = handoff
    narrative["chapter_instance_id"] = instance_id
    narrative["chapter_entry_checkpoint_id"] = ""
    narrative["choice_ready"] = False
    narrative.pop("phase_start_message_index", None)
    narrative.pop("active_phase_id", None)

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

    # Fronteira de prompt: preserva o histórico visual, mas inicia contexto novo.
    st.session_state.messages = []

    if persistence and st.session_state.run_id:
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
            active_user_role=st.session_state.active_user_role,
            story_ledger=story_ledger_text(st.session_state.story_state),
            scene_state=st.session_state.scene_state,
            story_state=st.session_state.story_state,
        )
        narrative["chapter_entry_checkpoint_id"] = entry_id

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


@st.cache_data(ttl=300, show_spinner=False)
def _cached_direct_script_rows(
    spreadsheet_id: str,
    worksheet: str,
    script_name: str,
    _service_account_info: dict,
) -> list[dict]:
    # Uma leitura por roteiro/planilha a cada 5 minutos, não por rerun,
    # mudança de input ou etapa do pipeline.
    return load_direct_script_rows(
        service_account_info=_service_account_info,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet,
        script_name=script_name,
    )


def _direct_script_rows(
    *, persistence: dict, chapter: dict, force_refresh: bool = False
) -> list[dict]:
    """Carrega a MINHA_SUGESTAO; cada turno ativo lê a versão mais recente."""
    if not persistence:
        raise PersistenceError(
            "O roteiro direto requer a planilha de persistência configurada."
        )

    worksheet = str(
        chapter.get("script_worksheet", "MINHA_SUGESTAO") or "MINHA_SUGESTAO"
    ).strip()
    script_name = str(chapter.get("script_name", "") or "").strip()
    if not script_name:
        raise PersistenceError(
            "Capítulo direto sem script_name. O roteiro deve ser identificado pela MINHA_SUGESTAO."
        )

    if force_refresh:
        # A interface usa cache para evitar leituras em cada rerun. No
        # processamento real de uma interação, descarte a fotografia antiga:
        # novas linhas de roteiro precisam ser reconhecidas imediatamente.
        _cached_direct_script_rows.clear()

    rows = deepcopy(_cached_direct_script_rows(
        persistence["spreadsheet_id"],
        worksheet,
        script_name,
        persistence["service_account_info"],
    ))
    if not rows:
        raise PersistenceError(
            f"Nenhuma linha do roteiro {script_name!r} foi encontrada em {worksheet!r}."
        )

    # DESCRIÇÃO INICIAL-CENA é contexto de CENA: autorada uma vez, mas válida
    # durante todas as linhas desta cena até que outro contexto de cena a substitua.
    scene_description = next(
        (
            str(row.get("initial_description", "") or "").strip()
            for row in rows
            if str(row.get("initial_description", "") or "").strip()
        ),
        "",
    )
    if scene_description:
        for row in rows:
            if not str(row.get("initial_description", "") or "").strip():
                row["initial_description"] = scene_description

    return rows


def _hybrid_script_rows(*, persistence: dict, chapter: dict) -> list[dict]:
    """Carrega o roteiro autoral atual da planilha em cada interação."""
    if not persistence:
        raise PersistenceError("A Carona híbrida requer a planilha de persistência configurada.")

    worksheet = str(
        chapter.get("script_worksheet", "ROTEIRO_REDATOR") or "ROTEIRO_REDATOR"
    ).strip()
    script_name = str(chapter.get("script_name", "Carona") or "Carona").strip()

    rows = load_sheet_script(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        worksheet_name=worksheet,
        script_name=script_name,
    )
    if not rows:
        raise PersistenceError(
            f"Nenhuma linha do roteiro {script_name!r} foi encontrada em {worksheet!r}."
        )
    return rows

def _block_script_rows(*, persistence: dict, chapter: dict) -> list[dict]:
    """Carrega os blocos dramáticos da planilha autoral nova."""
    if not persistence:
        raise PersistenceError(
            "O roteiro em blocos requer a planilha de persistência configurada."
        )

    worksheet = str(
        chapter.get("script_worksheet", "ROTEIRO_BLOCOS_TESTE")
        or "ROTEIRO_BLOCOS_TESTE"
    ).strip()

    rows = load_block_rows(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        worksheet_name=worksheet,
    )
    if not rows:
        raise PersistenceError(
            f"Nenhum bloco de roteiro foi encontrado em {worksheet!r}."
        )
    return rows


def _funnel_script_rows(*, persistence: dict, chapter: dict) -> list[dict]:
    """Carrega as cenas do funil atual diretamente da planilha."""
    if not persistence:
        raise PersistenceError(
            "A Carona em funil requer a planilha de persistência configurada."
        )

    worksheet = str(
        chapter.get("script_worksheet", "ROTEIRO_REDATOR")
        or "ROTEIRO_REDATOR"
    ).strip()

    rows = load_funnel_rows(
        service_account_info=persistence["service_account_info"],
        spreadsheet_id=persistence["spreadsheet_id"],
        worksheet_name=worksheet,
    )
    if not rows:
        raise PersistenceError(
            f"Nenhuma cena de funil foi encontrada em {worksheet!r}."
        )
    return rows


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
    "active_user_role": "PERSONAGEM_DA_CENA",
    "persistence_loaded": False,
    "persistence_error": "",
    "audit_error": "",
    "spreadsheet_url": "",
    "rollback_notice": "",
    "rollback_retry_text": "",
    "run_last_seq": 0,
    "route_checkpoints": [],
    "route_checkpoints_loaded_for_run": "",
    "hybrid_script_cache": {},
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
            saved_chapter_id = str(
                (saved.get("story_state") or {}).get("narrative", {}).get("chapter_id", "") or ""
            )
            saved_script_id = direct_script_id_from_chapter_id(saved_chapter_id)
            if saved_script_id and saved_script_id.casefold() != _first_sheet_script_id().casefold():
                valid_ids = {
                    str(item["script_id"]).casefold()
                    for item in load_direct_script_catalog(
                        service_account_info=persistence["service_account_info"],
                        spreadsheet_id=info["spreadsheet_id"],
                        worksheet_name="MINHA_SUGESTAO",
                    )
                }
                if saved_script_id.casefold() not in valid_ids:
                    _LOG.warning("Sessão antiga com capítulo inexistente: %s", saved_chapter_id)
                    saved = None
                    reset_local_story()

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
                archive_previous=True,
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

current_chapter = _runtime_get_chapter(_chapter_id())
st.caption(f"Capítulo atual: **{current_chapter.get('title', _chapter_id())}**")

# Orientação exclusiva ao jogador. O texto não entra no contexto da Mary,
# nem é encaminhado à Compreensão, ao Redator ou ao Diretor.
@st.cache_data(ttl=120, show_spinner=False)
def _cached_direct_info_board(spreadsheet_id: str, script_name: str, _service_account_info: dict) -> str:
    return load_direct_info_board(
        service_account_info=_service_account_info,
        spreadsheet_id=spreadsheet_id,
        script_name=script_name,
    )


if str(current_chapter.get("script_mode", "") or "").lower() == "direct_sheet" and persistence:
    _board_script = str(current_chapter.get("script_name", "") or "").strip()
    if _board_script:
        try:
            _player_board = _cached_direct_info_board(
                persistence["spreadsheet_id"],
                _board_script,
                persistence["service_account_info"],
            )
            if _player_board:
                st.info(_player_board)
        except Exception as _board_error:
            _LOG.warning("Quadro inicial indisponível para %s: %s", _board_script, _board_error)


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
        current_chapter.get("allowed_roles", ["PERSONAGEM_DA_CENA"]) or ["PERSONAGEM_DA_CENA"]
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
        role_options = ["PERSONAGEM_DA_CENA"]

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
    configured_model = str(
        st.secrets.get("MARY_DEFAULT_MODEL", "")
    ).strip()

    choices = list(DEFAULT_MODELS)
    if configured_model and configured_model not in choices:
        choices.insert(1, configured_model)

    selected = st.selectbox(
        "OpenRouter",
        choices,
        index=0,
        help="Padrão de teste: Gemini 3 Flash Preview. Outros modelos permanecem disponíveis para comparação.",
    )

    if selected == "Outro...":
        model = st.text_input("ID do modelo", placeholder="provedor/modelo").strip()
    else:
        model = selected

    temperature = st.slider("Temperatura", 0.2, 1.3, 0.6, 0.1)

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
                    active_user_role="PERSONAGEM_DA_CENA",
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
        if st.session_state.audit_error:
            st.caption("A história está salva; apenas a auditoria técnica encontrou um erro.")
            with st.expander("Detalhe da auditoria"):
                st.code(st.session_state.audit_error)
    elif st.session_state.persistence_error:
        st.warning("Persistência indisponível nesta sessão.")
        with st.expander("Detalhe técnico"):
            st.code(st.session_state.persistence_error)
    else:
        st.caption("Persistência Google Sheets ainda não configurada.")

    if (
        persistence
        and st.session_state.run_id
        and not st.session_state.persistence_error
    ):
        current_sidebar_chapter = _runtime_get_chapter(_chapter_id())
        direct_linear_runtime = (
            str(current_sidebar_chapter.get("script_mode", "") or "").strip().lower()
            == "direct_sheet"
        )
        with st.expander("Capítulo atual" if direct_linear_runtime else "Capítulos e rotas"):
            narrative_debug = st.session_state.story_state.get("narrative", {})
            caption_parts = [
                "Capítulo atual: " + str(narrative_debug.get("chapter_id", "")),
                "instância: " + str(narrative_debug.get("chapter_instance_id", "")),
            ]
            if not direct_linear_runtime:
                caption_parts.append(
                    "ramo: " + str(narrative_debug.get("branch_id", "main"))
                )
            st.caption(" · ".join(caption_parts))

            if st.button(
                "Reiniciar este capítulo sem apagar o histórico",
                use_container_width=True,
                key="restart_current_chapter",
            ):
                try:
                    restart_current_chapter(persistence)
                except Exception as exc:
                    st.error(f"Não foi possível reiniciar o capítulo: {exc}")

            if not direct_linear_runtime:
                if (
                    st.session_state.route_checkpoints_loaded_for_run
                    != st.session_state.run_id
                ):
                    try:
                        st.session_state.route_checkpoints = load_checkpoints(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            checkpoint_type="decision",
                        )
                        st.session_state.route_checkpoints_loaded_for_run = (
                            st.session_state.run_id
                        )
                    except Exception:
                        st.session_state.route_checkpoints = []
    
                decision_checkpoints = st.session_state.route_checkpoints
    
                if st.button(
                    "Atualizar decisões salvas",
                    use_container_width=True,
                    key="refresh_route_checkpoints",
                ):
                    try:
                        st.session_state.route_checkpoints = load_checkpoints(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            checkpoint_type="decision",
                        )
                        st.session_state.route_checkpoints_loaded_for_run = (
                            st.session_state.run_id
                        )
                        decision_checkpoints = st.session_state.route_checkpoints
                    except Exception as exc:
                        st.error(f"Não foi possível carregar decisões: {exc}")
    
                if decision_checkpoints:
                    st.markdown("**Explorar outra rota**")
                    selected_checkpoint = st.selectbox(
                        "Voltar a qual decisão?",
                        decision_checkpoints,
                        format_func=lambda item: (
                            f"#{int(item.get('source_seq', 0) or 0)} · "
                            f"{str(item.get('source_chapter_id', '') or '')}"
                        ),
                        key="branch_checkpoint_selector",
                    )
                    checkpoint_chapter_id = str(
                        selected_checkpoint.get("source_chapter_id", "") or ""
                    )
                    checkpoint_choices = chapter_choices(checkpoint_chapter_id)
                    if checkpoint_choices:
                        route_columns = st.columns(len(checkpoint_choices))
                        for route_column, route_choice in zip(
                            route_columns,
                            checkpoint_choices,
                        ):
                            with route_column:
                                route_choice_id = str(
                                    route_choice.get("id", "") or ""
                                )
                                if st.button(
                                    str(route_choice.get("label", route_choice_id)),
                                    use_container_width=True,
                                    key=(
                                        "fork_choice_"
                                        + str(selected_checkpoint.get("checkpoint_id", ""))
                                        + "_"
                                        + route_choice_id
                                    ),
                                ):
                                    try:
                                        activate_choice_from_checkpoint(
                                            checkpoint_id=str(
                                                selected_checkpoint.get(
                                                    "checkpoint_id",
                                                    "",
                                                )
                                            ),
                                            choice_id=route_choice_id,
                                            persistence=persistence,
                                        )
                                    except Exception as exc:
                                        st.error(
                                            f"Não foi possível abrir a rota: {exc}"
                                        )
                else:
                    st.caption(
                        "As decisões desta run aparecerão aqui à medida que forem criadas."
                    )
    
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
    chapter = _runtime_get_chapter(_chapter_id())

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

    opening_messages = [
        {"role": "system", "content": system_prompt},
        opening_instruction,
    ]
    model_audit = {
        "model": model,
        "fallback_model": fallback or "",
        "temperature": temperature,
        "system_prompt": system_prompt,
        "messages": deepcopy(opening_messages),
        "initial_raw_response": "",
        "retry_used": False,
        "retry_messages": [],
        "retry_raw_response": "",
        "final_raw_response": "",
        "mary_speech_raw": "",
        "mary_thought": "",
        "final_mary_text": "",
    }

    raw_answer = chat(
        api_key=api_key,
        model=model,
        fallback_model=fallback,
        messages=opening_messages,
        temperature=temperature,
    )
    model_audit["initial_raw_response"] = raw_answer
    mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
    narration_leak = looks_like_action_narration(mary_speech_raw)
    answer = sanitize_mary_output(mary_speech_raw)

    if not answer or narration_leak:
        opening_retry_messages = [
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
        ]
        model_audit["retry_used"] = True
        model_audit["retry_messages"] = deepcopy(opening_retry_messages)
        raw_answer = chat(
            api_key=api_key,
            model=model,
            fallback_model=fallback,
            messages=opening_retry_messages,
            temperature=max(0.2, min(float(temperature), 0.8)),
        )
        model_audit["retry_raw_response"] = raw_answer
        mary_intent, mary_speech_raw = parse_mary_response(raw_answer)
        narration_leak = looks_like_action_narration(mary_speech_raw)
        answer = sanitize_mary_output(mary_speech_raw)

    if not answer or narration_leak:
        raise OpenRouterError(
            "O modelo não produziu uma abertura verbal limpa para o novo capítulo."
        )

    model_audit["final_raw_response"] = raw_answer
    model_audit["mary_speech_raw"] = mary_speech_raw
    model_audit["mary_thought"] = mary_intent
    model_audit["final_mary_text"] = answer

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
        try:
            save_model_audit(
                service_account_info=persistence["service_account_info"],
                spreadsheet_id=info["spreadsheet_id"],
                spreadsheet_title=persistence["spreadsheet_title"],
                owner_email=persistence["owner_email"],
                run_id=st.session_state.run_id,
                seq=saved_seq,
                chapter_id=_chapter_id(),
                user_role=user_role,
                user_text="",
                audit=model_audit,
                branch_id=str(narrative.get("branch_id", "main") or "main"),
                chapter_instance_id=str(narrative.get("chapter_instance_id", "") or ""),
                chapter_turn=0,
            )
        except Exception as model_audit_exc:
            st.session_state.audit_error = str(model_audit_exc)
        try:
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
                branch_id=str(narrative.get("branch_id", "main") or "main"),
                chapter_instance_id=str(narrative.get("chapter_instance_id", "") or ""),
                chapter_turn=0,
            )
            st.session_state.audit_error = ""
        except Exception as audit_exc:
            # Auditoria é observabilidade; nunca deve derrubar a persistência principal.
            st.session_state.audit_error = str(audit_exc)


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
    if record.get("user_text"):
        with st.chat_message("user"):
            record_role = str(record.get("user_role", "JANIO") or "JANIO")
            if record_role == "PERSONAGEM_DA_CENA":
                st.caption("Personagem da cena")
            else:
                st.caption("Janio")
            st.markdown(record["user_text"])
    if record.get("mary_action"):
        _render_scene_action(record["mary_action"])
    with st.chat_message("assistant"):
        if record.get("mary_intent"):
            _render_mary_thought(record["mary_intent"])
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
choice_ready = bool(
    st.session_state.story_state.get("narrative", {}).get("choice_ready", False)
)
chapter_config_for_navigation = _runtime_get_chapter(chapter_id)
navigation_script_mode = str(
    chapter_config_for_navigation.get("script_mode", "") or ""
).strip().lower()

if navigation_script_mode == "direct_sheet" and bool(
    st.session_state.story_state.get("narrative", {}).get("direct_emotional_ending_blocked", False)
):
    st.divider()
    emotional_ending = st.session_state.story_state.get("narrative", {}).get("direct_emotion", {})
    if isinstance(emotional_ending, dict) and emotional_ending.get("rejected"):
        st.warning("Mary respeitou sua decisão de não se aproximar. A história se encerra aqui; retorne ou reinicie o capítulo para escolher outro caminho.")
    else:
        st.warning("Mary não gostou da sua atitude. Ela não deseja continuar esta história. Volte a uma etapa anterior ou reinicie o capítulo.")
elif navigation_script_mode == "direct_sheet" and choice_ready:
    st.divider()
    try:
        catalog = load_direct_script_catalog(
            service_account_info=persistence["service_account_info"],
            spreadsheet_id=persistence["spreadsheet_id"],
            worksheet_name=str(
                chapter_config_for_navigation.get(
                    "script_worksheet",
                    "MINHA_SUGESTAO",
                )
                or "MINHA_SUGESTAO"
            ),
        ) if persistence else []
        current_script_id = str(
            chapter_config_for_navigation.get("script_name", "") or ""
        ).strip()
        next_script = next_direct_script(catalog, current_script_id)
        if next_script:
            next_script_id = str(next_script.get("script_id", "") or "").strip()
            next_title = str(
                next_script.get("script_name", next_script_id) or next_script_id
            ).strip()
            executable_rows = int(
                next_script.get("executable_row_count", 0) or 0
            )
            st.subheader("Próximo capítulo")
            st.caption(
                f"{current_script_id} concluído. Próximo roteiro reconhecido na planilha: "
                f"{next_script_id}."
            )
            if executable_rows <= 0:
                st.warning(
                    f"{next_script_id} já está catalogado pela planilha, mas ainda não possui "
                    "Fala-guia preenchida. O avanço ficará disponível quando o roteiro tiver "
                    "ao menos uma linha executável."
                )
            elif st.button(
                f"Continuar: {next_title}",
                key=f"direct_continue_{next_script_id}",
                use_container_width=True,
            ):
                activate_direct_sheet_chapter(
                    script_id=next_script_id,
                    persistence=persistence,
                )
        else:
            st.success("Roteiro concluído. Não há capítulo posterior cadastrado na MINHA_SUGESTAO.")
    except Exception as exc:
        st.error(f"Não foi possível localizar o próximo roteiro na planilha: {exc}")

elif (
    navigation_script_mode != "direct_sheet"
    and chapter_ready_for_choice(chapter_id, chapter_turns, choice_ready)
):
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


direct_ui_row: dict = {}
direct_ui_error = ""
try:
    ui_chapter = _runtime_get_chapter(_chapter_id())
    if (
        persistence
        and str(ui_chapter.get("script_mode", "") or "").strip().lower() == "direct_sheet"
    ):
        ui_rows = _direct_script_rows(
            persistence=persistence,
            chapter=ui_chapter,
        )
        ui_state = ensure_direct_state(
            st.session_state.story_state.setdefault("narrative", {}),
            ui_rows,
        )
        direct_ui_row = current_direct_row(ui_rows, ui_state)
        loop_ui = st.session_state.story_state.get("narrative", {}).get("direct_hurt_loop", {})
        if isinstance(loop_ui, dict) and loop_ui.get("active") and ui_rows:
            loop_source = direct_ui_row or ui_rows[0]
            direct_ui_row = dict(loop_source.get("_emotional_loop_row") or direct_ui_row)
except Exception as exc:
    direct_ui_error = str(exc)

# A faixa emocional é reconstruída a cada rerun a partir do estado persistido.
loop_ui_status = st.session_state.story_state.get("narrative", {}).get("direct_hurt_loop", {})
if (navigation_script_mode == "direct_sheet" and isinstance(loop_ui_status, dict)
        and loop_ui_status.get("active") and not loop_ui_status.get("exhausted")):
    st.warning(
        "Mary está contrariada. O roteiro principal está suspenso enquanto ela avalia "
        "uma reparação contextual. "
        f"Interações sem reconciliação: {int(loop_ui_status.get('attempts', 0) or 0)}/"
        f"{int(loop_ui_status.get('max_attempts', 3) or 3)}."
    )

automatic_emitted = bool(
    direct_ui_row
    and is_automatic_direct_row(direct_ui_row)
    and int(ui_state.get("automatic_emitted_order", 0) or 0)
        == int(direct_ui_row.get("order", 0) or 0)
    and not choice_ready
)
automatic_turn = bool(
    direct_ui_row
    and is_automatic_direct_row(direct_ui_row)
    and not automatic_emitted
    and not choice_ready
)
blocked_turn = bool(
    direct_ui_row
    and is_blocked_direct_row(direct_ui_row)
    and int(ui_state.get("awaiting_reply_order", 0) or 0)
        != int(direct_ui_row.get("order", 0) or 0)
    and not choice_ready
)
mary_first_turn = bool(automatic_turn or blocked_turn)
auto_retry_key = _direct_auto_retry_key(
    _chapter_id(),
    str(st.session_state.story_state.get("narrative", {}).get("chapter_instance_id", "") or ""),
    int(direct_ui_row.get("order", 0) or 0) if direct_ui_row else 0,
)
if automatic_emitted:
    # A resposta desta linha já está publicada. O botão apenas move a ORDEM;
    # não chama modelos, não gera novo turno e não duplica os logs.
    user_text = None
    if st.button(
        "Prosseguir",
        key=f"auto_advance_{_chapter_id()}_{direct_ui_row.get('order', 0)}",
        use_container_width=True,
        type="primary",
    ):
        state_before_advance = deepcopy(st.session_state.story_state)
        try:
            # Releia a planilha também na navegação: uma linha recém-inserida
            # depois da automática não pode desaparecer por cache antigo.
            navigation_rows = _direct_script_rows(
                persistence=persistence,
                chapter=ui_chapter,
                force_refresh=True,
            )
            if advance_emitted_automatic_line(ui_state, navigation_rows):
                narrative_advance = st.session_state.story_state.setdefault("narrative", {})
                if direct_script_ready_for_choice(ui_state):
                    narrative_advance["choice_ready"] = True
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
                st.rerun()
        except Exception as exc:
            st.session_state.story_state = state_before_advance
            st.error(f"Não foi possível avançar a linha automática: {exc}")
elif mary_first_turn:
    if automatic_turn:
        # Entrar na linha executa sua resposta sem turno vazio do usuário.
        # Se o modelo falhou, evite nova cobrança involuntária em cada rerun.
        if st.session_state.get(auto_retry_key, False):
            user_text = (
                "Prosseguir"
                if st.button(
                    "Tentar novamente",
                    key=f"retry_{auto_retry_key}",
                    use_container_width=True,
                )
                else None
            )
        else:
            user_text = "Prosseguir"
        st.caption("Mary conduz esta linha automaticamente. Depois, Prosseguir avançará o roteiro.")
    else:
        user_text = (
            "Prosseguir"
            if st.button(
                "Prosseguir",
                key=f"mary_first_continue_{_chapter_id()}_{direct_ui_row.get('order', 0)}",
                use_container_width=True,
                type="primary",
            )
            else None
        )
        st.caption("Mary inicia esta passagem. Depois da fala dela, o campo do personagem será liberado.")
else:
    if user_role == "JANIO":
        placeholder = "Fale ou dirija a cena como Janio..."
    else:
        temporary_name = str(
            st.session_state.scene_state.get("temporary_character", {}).get("name", "")
            or "personagem da cena"
        ).strip()
        placeholder = f"Fale ou dirija a cena como {temporary_name}..."
    emotional_ending_blocked = bool(st.session_state.story_state.get("narrative", {}).get("direct_emotional_ending_blocked", False))
    user_text = st.chat_input(placeholder, disabled=bool(direct_ui_error) or emotional_ending_blocked)

if direct_ui_error:
    st.error(f"Não foi possível determinar o modo da linha atual: {direct_ui_error}")


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

        if mary_first_turn:
            parsed_input = {
                "scene_direction": "",
                "dialogue": "",
            }
        else:
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

        if scene_direction or user_spoke:
            user_message_parts = [f"[PAPEL={user_role}]"]
            if scene_direction:
                user_message_parts.append(f"[DIREÇÃO/ENCENAÇÃO] {scene_direction}")
            if dialogue_text:
                user_message_parts.append(f"[FALA] {dialogue_text}")
            st.session_state.messages.append(
                {"role": "user", "content": "\n".join(user_message_parts)}
            )

        current_turn_number = _chapter_turns() + 1
        chapter_config = _runtime_get_chapter(_chapter_id())
        narrative_state = st.session_state.story_state.setdefault("narrative", {})
        script_mode = str(chapter_config.get("script_mode", "") or "").strip().lower()
        director_chapter_prompt = ""
        direct_rows: list[dict] = []
        direct_state: dict | None = None
        direct_row: dict = {}
        direct_registration: dict = {}
        defer_locked_entry = False

        hybrid_rows: list[dict] = []
        hybrid_state: dict | None = None
        hybrid_selected_row: dict = {}
        hybrid_continuity = ""
        hybrid_closing_convergence = ""

        block_rows: list[dict] = []
        block_state: dict | None = None
        block_row: dict = {}
        block_dependency: dict = {}
        block_progress: dict = {}

        funnel_rows: list[dict] = []
        funnel_state: dict | None = None
        funnel_row: dict = {}
        funnel_evaluation: dict = {}
        funnel_progress: dict = {}

        if script_mode == "direct_sheet":
            direct_rows = _direct_script_rows(
                persistence=persistence,
                chapter=chapter_config,
                force_refresh=True,
            )
            direct_state = ensure_direct_state(
                narrative_state,
                direct_rows,
            )
            active_hurt_loop = narrative_state.get("direct_hurt_loop", {})
            in_hurt_loop = bool(isinstance(active_hurt_loop, dict) and active_hurt_loop.get("active"))
            if (user_spoke or bool(scene_direction)) and not in_hurt_loop:
                direct_registration = register_direct_user_reply(
                    direct_state,
                    direct_rows,
                    dialogue_text,
                    scene_direction=scene_direction,
                )
            direct_row = current_direct_row(
                direct_rows,
                direct_state,
            )
            if in_hurt_loop and not direct_row and direct_rows:
                direct_row = dict(direct_rows[0])  # Fonte do LOOP quando a última linha foi interrompida.
            current_phase = {
                "id": str(direct_row.get("line_id", "") or "roteiro_concluido"),
                "goal": str(direct_row.get("speech_guide", "") or "encerrar a Carona"),
            }
            registration_before = (
                direct_registration.get("state_before", {})
                if isinstance(direct_registration, dict)
                else {}
            )
            defer_locked_entry = bool(
                user_spoke
                and not mary_first_turn
                and int(registration_before.get("awaiting_reply_order", 0) or 0) > 0
                and direct_row
                and (
                    is_automatic_direct_row(direct_row)
                    or is_blocked_direct_row(direct_row)
                )
            )
        elif script_mode == "block_sheet":
            block_rows = _block_script_rows(
                persistence=persistence,
                chapter=chapter_config,
            )
            block_state = ensure_block_state(
                narrative_state,
                block_rows,
            )
            block_row = current_block_row(
                block_rows,
                block_state,
            )
            current_phase = {
                "id": str(block_row.get("block_id", "") or ""),
                "goal": str(block_row.get("objective", "") or ""),
            }
        elif script_mode == "funnel_sheet":
            funnel_rows = _funnel_script_rows(
                persistence=persistence,
                chapter=chapter_config,
            )
            funnel_state = ensure_funnel_state(
                narrative_state,
                funnel_rows,
            )
            funnel_row = current_funnel_row(
                funnel_rows,
                funnel_state,
            )
            current_phase = {
                "id": str(funnel_row.get("scene_id", "") or ""),
                "goal": str(funnel_row.get("objective", "") or ""),
            }
        elif script_mode == "hybrid_phase_sheet":
            hybrid_rows = _hybrid_script_rows(
                persistence=persistence,
                chapter=chapter_config,
            )
            hybrid_state = ensure_carona_state(narrative_state)
            if user_spoke:
                register_user_reply(hybrid_state, dialogue_text)
            current_phase, hybrid_selected_row, hybrid_continuity = select_carona_line(
                hybrid_rows,
                hybrid_state,
                st.session_state.scene_state,
            )
        else:
            current_phase = chapter_phase(_chapter_id(), current_turn_number)

        if script_mode == "direct_sheet" and defer_locked_entry:
            # A fala real do usuário apenas fecha a linha interativa anterior.
            # Se a próxima linha exige iniciativa de Mary (automática ou bloqueada),
            # ela NÃO é executada com essa fala. Persiste-se a resposta do usuário
            # e a UI volta exibindo o botão Prosseguir.
            # Resposta curta à entrada final da linha anterior; a próxima fica pendente.
            previous_index = int(registration_before.get("index", 0) or 0)
            previous_row = direct_rows[previous_index] if 0 <= previous_index < len(direct_rows) else {}
            transition_prompt = (
                "Você é Mary. Responda à última intervenção do interlocutor no contexto "
                "da linha que acabou de terminar. Responda perguntas e reconheça ações, "
                "sem antecipar a próxima linha do roteiro, que só será executada após Prosseguir. "
                "Fale de modo natural, sucinto, sem narração ou instruções técnicas. "
                "Respeite a memória local e os limites de revelação da linha anterior.\\n"
                "MEMÓRIA LOCAL: " + str(previous_row.get("instant_memory", "") or "")
                + "\\nREVELAÇÃO: " + str(previous_row.get("revelation_policy", "") or "")
            )
            bridge_messages = [
                {"role": "system", "content": transition_prompt},
                *[
                    {"role": msg["role"], "content": str(msg.get("content", ""))}
                    for msg in st.session_state.messages[-10:]
                    if msg.get("role") in {"user", "assistant"}
                ],
            ]
            try:
                bridge_answer = sanitize_mary_output(chat(
                    api_key=api_key, model=model, fallback_model=fallback,
                    messages=bridge_messages, temperature=temperature, max_tokens=240,
                ))
                if not bridge_answer:
                    raise OpenRouterError("Resposta de transição vazia.")
            except Exception:
                st.session_state.story_state = deepcopy(pre_turn_snapshot["story_state"])
                st.session_state.messages = messages_before_turn
                raise
            st.session_state.messages.append({"role": "assistant", "content": bridge_answer})
            narrative_state["chapter_turns"] = int(
                narrative_state.get("chapter_turns", 0) or 0
            ) + 1
            transition_record = {
                "seq": 0,
                "caption": "",
                "direction": scene_direction,
                "mary_action": "",
                "hook_resolution": "",
                "mary_intent": "",
                "user_role": user_role,
                "user_text": dialogue_text,
                "mary_text": bridge_answer,
                "branch_id": str(narrative_state.get("branch_id", "main") or "main"),
                "chapter_instance_id": str(
                    narrative_state.get("chapter_instance_id", "") or ""
                ),
                "chapter_id": _chapter_id(),
                "chapter_turn": int(narrative_state.get("chapter_turns", 0) or 0),
            }
            st.session_state.turn_records.append(transition_record)

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
                    turn_record=transition_record,
                    pre_turn_snapshot=pre_turn_snapshot,
                )
                transition_record["seq"] = saved_seq
                st.session_state.run_last_seq = saved_seq

            st.rerun()

        current_phase_id = str(current_phase.get("id", "") or "").strip()
        current_phase_goal = str(current_phase.get("goal", "") or "").strip()
        previous_phase_id = str(
            st.session_state.scene_state.get("chapter_phase", "") or ""
        ).strip()
        phase_changed = bool(current_phase_id) and current_phase_id != previous_phase_id

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
            if script_mode not in {"direct_sheet", "hybrid_phase_sheet", "funnel_sheet", "block_sheet"}:
                scene_for_director["return_anchor"] = ""

        direct_interpretation = {}
        emotional_notice = ""
        if script_mode == "direct_sheet":
            # O handoff já é persistido na mudança de capítulo. Entregue-o
            # somente no primeiro turno do novo roteiro: evita importar o
            # histórico inteiro ou reencenar a despedida em linhas futuras.
            direct_handoff_text = (
                _handoff_text(st.session_state.story_state)
                if current_turn_number == 1 else ""
            )
            handoff_record = narrative_state.get("handoff", {})
            if not isinstance(handoff_record, dict):
                handoff_record = {}
            handoff_previous_mary = (
                str(handoff_record.get("mary_text", "") or "").strip()
                if direct_handoff_text and direct_handoff_text != "(nenhum)" else ""
            )
            chapter_emotion_id = str(narrative_state.get("chapter_id", "") or "")
            emotion = narrative_state.get("direct_emotion", {})
            if not isinstance(emotion, dict) or emotion.get("chapter_id") != chapter_emotion_id:
                emotion = {"chapter_id": chapter_emotion_id, "hurt": False, "continuation_allowed": True, "rejected": False}
                narrative_state["direct_emotion"] = emotion
                narrative_state["direct_emotional_ending_blocked"] = False
            # Enquanto o LOOP está ativo, as regras ficam ancoradas na linha
            # que provocou o conflito, nunca na próxima linha do cursor.
            loop_snapshot = narrative_state.get("direct_hurt_loop", {})
            loop_active = bool(isinstance(loop_snapshot, dict) and loop_snapshot.get("active"))
            # O usuário pode ter acabado de responder à linha anterior.
            # register_direct_user_reply já avançou o cursor; para avaliar
            # a contrariedade use a linha à qual ele realmente respondeu,
            # não a próxima missão ainda não iniciada.
            authored_trigger_row = direct_row
            origin_index = int(registration_before.get("index", -1) if registration_before else -1)
            if (user_spoke and not loop_active
                    and int(registration_before.get("awaiting_reply_order", 0) or 0) > 0
                    and 0 <= origin_index < len(direct_rows)):
                authored_trigger_row = direct_rows[origin_index]
            negative_rule = str((loop_snapshot.get("negative_rule") if loop_active else authored_trigger_row.get("negative_prompt", "")) or "")
            wounded_style = str((loop_snapshot.get("wounded_style") if loop_active else authored_trigger_row.get("hurt_style", "")) or "")
            loop_authorial_row = dict(direct_row.get("_emotional_loop_row") or {})
            loop_direction = str(loop_authorial_row.get("speech_guide", "") or "")
            loop_hurt_rule = str(loop_authorial_row.get("hurt_style", "") or "")
            loop_negative_rule = str(loop_authorial_row.get("negative_prompt", "") or "")
            # Para interpretar a fala, não antecipe a memória ou a revelação
            # da próxima linha. No LOOP, a linha especial prevalece e pode
            # herdar apenas o contexto factual da origem.
            understanding_row = dict(loop_authorial_row if loop_active else authored_trigger_row)
            if loop_active and isinstance(loop_snapshot, dict):
                for context_key, saved_key in (
                    ("instant_memory", "origin_instant_memory"),
                    ("revelation_policy", "origin_revelation_policy"),
                    ("initial_description", "origin_initial_description"),
                ):
                    understanding_row[context_key] = str(
                        understanding_row.get(context_key) or loop_snapshot.get(saved_key, "") or ""
                    )
                if direct_rows:
                    understanding_row["permanent_memory"] = direct_rows[0].get("permanent_memory", "")
                    understanding_row["physical_memory"] = direct_rows[0].get("physical_memory", "")
            previous_mary_text = next(
                (
                    str(message.get("content", "") or "").strip()
                    for message in reversed(messages_before_turn)
                    if str(message.get("role", "") or "").strip().lower() == "assistant"
                    and str(message.get("content", "") or "").strip()
                ),
                handoff_previous_mary,
            )
            # Uma única chamada de compreensão: recebe somente passado/presente
            # já estabelecidos. Nunca recebe a fala-guia nem roteiro futuro.
            recent_user_facts = narrative_state.get("direct_recent_user_facts", [])
            if not isinstance(recent_user_facts, list):
                recent_user_facts = []
            previous_conversation_state = normalize_conversation_state(
                narrative_state.get("direct_conversation_state", {})
            )

            detected_character_name = extract_direct_character_name(
                direct_row,
                dialogue_text,
            )
            if detected_character_name:
                temporary = st.session_state.scene_state.get("temporary_character", {})
                if not isinstance(temporary, dict):
                    temporary = {}
                temporary = dict(temporary)
                temporary.update(
                    {
                        "active": True,
                        "name": detected_character_name,
                        "user_can_play": True,
                    }
                )
                st.session_state.scene_state["temporary_character"] = temporary
                scene_for_director["temporary_character"] = deepcopy(temporary)

            temporary_character = scene_for_director.get("temporary_character", {})
            if not isinstance(temporary_character, dict):
                temporary_character = {}
            active_interlocutor = (
                ""
                if automatic_turn
                else " | ".join(
                    part
                    for part in [
                        "papel=" + str(scene_for_director.get("user_role", "") or "").strip(),
                        "nome=" + str(temporary_character.get("name", "") or "").strip(),
                        "descrição=" + str(temporary_character.get("description", "") or "").strip(),
                        "relação=" + str(temporary_character.get("relation_to_mary", "") or "").strip(),
                        "gênero=" + str(temporary_character.get("gender", "") or "").strip(),
                    ]
                    if part.split("=", 1)[1]
                )
            )

            automatic_direct_turn = bool(
                automatic_turn and is_automatic_direct_row(direct_row)
            )
            blocked_direct_turn = bool(
                (blocked_turn and is_blocked_direct_row(direct_row))
            )
            if automatic_direct_turn:
                direct_interpretation = {
                    "relation_to_previous": (
                        "continuação automática autorizada pelo botão Prosseguir; "
                        "não houve nova fala do interlocutor"
                    ),
                    "move": "prosseguir a sequência interna de Mary",
                    "literal_meaning": (
                        "O usuário apenas autorizou a continuação da cena; "
                        "não acrescentou conteúdo narrativo."
                    ),
                    "user_obligation": {
                        "exists": False,
                        "requirement": "",
                    },
                    "recent_user_facts": list(recent_user_facts[-16:]),
                    "automatic_turn": True,
                }
            elif blocked_direct_turn:
                direct_interpretation = {
                    "relation_to_previous": (
                        "iniciativa de Mary autorizada pelo botão Prosseguir; "
                        "não houve nova fala do interlocutor"
                    ),
                    "move": "Mary inicia a interação da linha atual",
                    "literal_meaning": (
                        "O usuário apenas autorizou Mary a tomar a iniciativa; "
                        "a fala atual deve partir de Mary e terminar aguardando resposta."
                    ),
                    "user_obligation": {
                        "exists": False,
                        "requirement": "",
                    },
                    "recent_user_facts": list(recent_user_facts[-16:]),
                    "blocked_turn": True,
                }
            else:
                direct_interpretation = analyze_user_understanding(
                    api_key=api_key,
                    model=director_model,
                    fallback_model=fallback,
                    user_text=dialogue_text,
                    user_scene_direction=scene_direction,
                    previous_mary_text=previous_mary_text,
                    recent_messages=messages_before_turn,
                    recent_user_facts=recent_user_facts,
                    active_interlocutor=active_interlocutor,
                    previous_conversation_state=previous_conversation_state,
                    instant_memory=str(understanding_row.get("instant_memory", "") or ""),
                    permanent_memory=str(understanding_row.get("permanent_memory", "") or ""),
                    physical_memory=str(understanding_row.get("physical_memory", "") or ""),
                    initial_description=str(understanding_row.get("initial_description", "") or ""),
                    revelation_policy=str(understanding_row.get("revelation_policy", "") or ""),
                )
            assessment = {}
            # O LOOP só é habilitado quando há uma linha LOOP autoral e
            # um critério de contrariedade definido na planilha. Não existe
            # motivo emocional presumido pelo código.
            # Roteiros antigos sem linha LOOP conservam a avaliação emocional
            # legada; capítulos com LOOP podem declarar os critérios por linha.
            has_emotional_policy = bool(
                (negative_rule and wounded_style)
                or (loop_direction and (negative_rule or wounded_style))
            )
            if has_emotional_policy and dialogue_text.strip() and not (automatic_direct_turn or blocked_direct_turn):
                try:
                    assessment_raw = chat(
                        api_key=api_key, model=director_model, fallback_model=fallback,
                        temperature=0.0, max_tokens=350,
                        messages=[
                            {"role": "system", "content": (
                                "Você é um classificador de fatos emocionais de uma cena ficcional. "
                                "Não decida como Mary deve falar, agir, perdoar ou encerrar a cena. "
                                "Compare a fala atual com as expectativas, os limites e as condições "
                                "autorais da LINHA ATIVA e da LINHA LOOP informadas abaixo. "
                                "Retorne APENAS JSON com violation, frustration, repair_attempt, "
                                "forgiven, rejected (booleanos), reason (texto), speaker (nome de "
                                "quem realmente falou; vazio se incerto) e repair_evidence "
                                "(trecho LITERAL da fala atual, ou vazio). "
                                "violation=true somente se a fala afronta limites explícitos da planilha. "
                                "frustration=true somente se contraria expectativa concreta prevista "
                                "pela situação ou por ORGULHO FERIDO; nunca invente uma expectativa. "
                                "Não confunda recusa pontual com rejeição pessoal definitiva: "
                                "rejected=true apenas quando há rejeição clara da aproximação pessoal. "
                                "Uma recusa cordial pode ou não contrariar Mary, conforme a planilha. "
                                "Humor, brincadeira e disponibilidade não são automaticamente desrespeito. "
                                "No LOOP, repair_attempt identifica tentativa concreta de reparar; "
                                "forgiven=true apenas se a fala oferece evidência suficiente de reparação "
                                "conforme a direção autoral do LOOP e o conflito estabelecido. "
                                "Não invente perdão; não exija fórmula fixa de desculpas. "
                                "Não atribua atos de um personagem a outro. A saída deve representar "
                                "somente o que o interlocutor fez e o que o contrato autoral permite concluir."
                            )},
                            {"role": "user", "content": (
                                "ORGULHO FERIDO DA LINHA DE ORIGEM: " + wounded_style +
                                "\\nPROMPT NEGATIVO DA LINHA DE ORIGEM: " + negative_rule +
                                "\\nORIENTAÇÃO AUTORAL DO LOOP: " + loop_direction +
                                "\\nORGULHO FERIDO DA LINHA LOOP: " + loop_hurt_rule +
                                "\\nLIMITES DA LINHA LOOP: " + loop_negative_rule +
                                "\\nMEMÓRIA LOCAL: " + str(understanding_row.get("instant_memory", "") or "") +
                                "\\nINTERLOCUTOR REGISTRADO: " + active_interlocutor +
                                "\\nCOMPREENSÃO DA FALA: " + str(direct_interpretation.get("literal_meaning", "") or "") +
                                "\\nESTADO: " + json.dumps(emotion, ensure_ascii=False) +
                                "\\nCONTEXTO: " + previous_mary_text[-1000:] +
                                "\\nUSUÁRIO: " + dialogue_text
                            )},
                        ],
                    )
                    found = re.search(r"\{[\s\S]*\}", str(assessment_raw or ""))
                    assessment = json.loads(found.group(0)) if found else {}
                    # Estados emocionais pertencem ao personagem que os provocou,
                    # não a todos os participantes da cena. Preserva o legado
                    # quando a autoria da fala atual for incerta.
                    speaker = str(assessment.get("speaker", "") or "").strip()
                    if speaker:
                        speaker_key = speaker.casefold()
                        active_key = str(emotion.get("active_speaker", "") or "").casefold()
                        by_speaker = emotion.get("speaker_states", {})
                        if not isinstance(by_speaker, dict):
                            by_speaker = {}
                        if active_key and speaker_key != active_key:
                            by_speaker[active_key] = {
                                "hurt": bool(emotion.get("hurt")),
                                "rejected": bool(emotion.get("rejected")),
                                "continuation_allowed": bool(emotion.get("continuation_allowed", True)),
                            }
                            restored = by_speaker.get(speaker_key, {})
                            emotion["hurt"] = bool(restored.get("hurt", False))
                            emotion["rejected"] = bool(restored.get("rejected", False))
                            emotion["continuation_allowed"] = bool(restored.get("continuation_allowed", True))
                        emotion["active_speaker"] = speaker_key
                        emotion["speaker_states"] = by_speaker
                    if assessment.get("rejected") is True:
                        emotion["hurt"] = True
                        emotion["rejected"] = True
                        emotion["continuation_allowed"] = False
                        emotional_notice = "Mary percebeu que você não deseja proximidade. Ela respeitará sua decisão."
                    elif assessment.get("violation") is True or assessment.get("frustration") is True:
                        emotion["hurt"] = True
                        emotion["continuation_allowed"] = False
                        emotional_notice = ("Mary ficou contrariada com a situação." if assessment.get("frustration")
                                            and not assessment.get("violation") else "Mary ficou decepcionada com sua atitude.")
                    elif (emotion.get("hurt") and assessment.get("forgiven") is True
                          and len(str(assessment.get("repair_evidence", "") or "").strip()) >= 5
                          and str(assessment.get("repair_evidence", "") or "").strip().casefold() in dialogue_text.casefold()):
                        # Reconciliação validada encerra mágoa e rejeição anteriores
                        # APENAS para este interlocutor, sem apagar o histórico.
                        emotion["hurt"] = False
                        emotion["rejected"] = False
                        emotion["continuation_allowed"] = True
                        emotional_notice = "Mary aceitou a reparação e retomou a conversa."
                    if speaker:
                        emotion["speaker_states"][speaker_key] = {
                            "hurt": bool(emotion.get("hurt")),
                            "rejected": bool(emotion.get("rejected")),
                            "continuation_allowed": bool(emotion.get("continuation_allowed", True)),
                        }
                    emotion["last_assessment"] = assessment
                    narrative_state["direct_emotion"] = emotion
                except Exception as exc:
                    _LOG.warning("Falha na avaliação emocional; estado preservado: %s", exc)
            # O LOOP autoral é um desvio, não uma linha consumível do roteiro.
            loop = narrative_state.get("direct_hurt_loop", {})
            if not isinstance(loop, dict) or loop.get("chapter_id") != chapter_emotion_id:
                loop = {"chapter_id": chapter_emotion_id, "active": False, "attempts": 0}
            loop_row = dict(direct_row.get("_emotional_loop_row") or {})
            if (not loop.get("active") and loop_row
                    and (assessment.get("violation") is True
                         or assessment.get("frustration") is True
                         or assessment.get("rejected") is True)):
                loop.update({"active": True, "attempts": 0,
                             "max_attempts": hurt_loop_max_interactions(loop_row),
                             "speaker": str(emotion.get("active_speaker", "") or ""),
                             "origin_order": int(authored_trigger_row.get("order", 0) or 0),
                             "wounded_style": wounded_style,
                             "negative_rule": negative_rule,
                             "origin_instant_memory": str(authored_trigger_row.get("instant_memory", "") or ""),
                             "origin_revelation_policy": str(authored_trigger_row.get("revelation_policy", "") or ""),
                             "origin_initial_description": str(authored_trigger_row.get("initial_description", "") or "")})
                # Ao contrariar a missão da linha atual, sua resposta é o fato
                # real ocorrido; o cursor retorna à linha seguinte após reparação.
                advanced_from_previous = bool(
                    (direct_registration.get("state_before", {}) if isinstance(direct_registration, dict) else {}).get("awaiting_reply_order", 0)
                )
                if not advanced_from_previous and direct_state and direct_row:
                    idx = int(direct_state.get("index", 0) or 0)
                    order = int(direct_row.get("order", 0) or 0)
                    completed = set(direct_state.get("completed_orders", []) or [])
                    completed.add(order)
                    direct_state["completed_orders"] = sorted(completed)
                    direct_state["index"] = min(idx + 1, len(direct_rows))
                    direct_state["awaiting_reply_order"] = 0
                    direct_state["line_dialogue"] = []
                    direct_state["completed"] = direct_state["index"] >= len(direct_rows)
                    direct_state["current_order"] = (int(direct_rows[direct_state["index"]].get("order", 0) or 0)
                                                     if not direct_state["completed"] else 0)
            if loop.get("active"):
                # A mágoa e a reconciliação pertencem ao interlocutor que
                # originou o LOOP. Fala de Silvia/outro personagem nunca
                # libera o roteiro nem apaga a pendência desse interlocutor.
                loop_owner = str(loop.get("speaker", "") or "").casefold()
                assessed_owner = str(assessment.get("speaker", "") or "").casefold()
                owner_reconciled = bool(
                    loop_owner and assessed_owner == loop_owner
                    and assessment.get("forgiven") is True
                    and not emotion.get("hurt")
                )
                if owner_reconciled:
                    loop["active"] = False
                    loop["attempts"] = 0
                    loop["exhausted"] = False
                    direct_row = current_direct_row(direct_rows, direct_state)
                    emotional_notice = "Mary aceitou a reparação; o roteiro será retomado."
                else:
                    # Cada intervenção válida do interlocutor responsável no LOOP
                    # consome uma oportunidade, inclusive novas ofensas, recusas
                    # e evasivas. Não confundir oportunidade com pedido de desculpas.
                    # Falas de outros personagens não penalizam o responsável.
                    assessed_speaker = str(assessment.get("speaker", "") or "").strip().casefold()
                    loop_speaker = str(loop.get("speaker", "") or "").strip().casefold()
                    same_speaker = bool(assessed_speaker and loop_speaker and assessed_speaker == loop_speaker)
                    max_attempts = max(1, int(loop.get("max_attempts", 3) or 3))
                    if dialogue_text.strip() and user_spoke and same_speaker:
                        loop["attempts"] = min(max_attempts, int(loop.get("attempts", 0) or 0) + 1)
                    if int(loop.get("attempts", 0) or 0) >= max_attempts:
                        loop["exhausted"] = True
                    direct_row = dict(loop_row)
                    direct_row["instant_memory"] = str(direct_row.get("instant_memory") or loop.get("origin_instant_memory", "") or "")
                    direct_row["revelation_policy"] = str(direct_row.get("revelation_policy") or loop.get("origin_revelation_policy", "") or "")
                    direct_row["initial_description"] = str(direct_row.get("initial_description") or loop.get("origin_initial_description", "") or "")
                    # A linha LOOP é soberana durante o desvio; instruções da
                    # origem permanecem como contexto, não substituem o LOOP.
                    direct_row["negative_prompt"] = loop_negative_rule or negative_rule
                    direct_row["hurt_style"] = loop_hurt_rule or wounded_style
                    direct_row["permanent_memory"] = str(direct_rows[0].get("permanent_memory", "") or "") if direct_rows else ""
                    direct_row["physical_memory"] = str(direct_rows[0].get("physical_memory", "") or "") if direct_rows else ""
                    direct_interpretation["emotional_status"] = (
                        "Orgulho ferido ativo; interlocutor=" + str(loop.get("speaker", "")) +
                        "; interações sem reconciliação=" + str(loop.get("attempts", 0)) +
                        "/" + str(loop.get("max_attempts", 3)) + ". "
                        "Mary interpreta a reação conforme os guias e limites da LINHA LOOP; "
                        "não presuma perdão, culpa, intensidade nem atitude fora da planilha."
                    )
            narrative_state["direct_hurt_loop"] = loop
            if emotion.get("hurt") or loop.get("active"):
                direct_row = dict(direct_row)
                # Quando a linha LOOP traz estilo/atitude, ele governa a cena.
                # O texto de Orgulho Ferido é a orientação autoral da condição.
                active_hurt_style = str(direct_row.get("hurt_style", "") or wounded_style)
                if active_hurt_style:
                    direct_row["style"] = (str(direct_row.get("style", "") or "") +
                        " | ORGULHO FERIDO AUTORAL: " + active_hurt_style)
                # Não injetar comandos na memória local de fatos.
                direct_interpretation.setdefault("emotional_status",
                    "Mágoa persistente; limites e proximidade avaliados pela conversa real.")
            grounded_facts = direct_interpretation.get("recent_user_facts", [])
            if isinstance(grounded_facts, list):
                narrative_state["direct_recent_user_facts"] = [
                    str(value or "").strip()
                    for value in grounded_facts[-16:]
                    if str(value or "").strip()
                ]

            # A mesma compreensão operacional é persistida para auditoria.
            # Assim o log mostra exatamente o que o Redator recebeu.
            understanding_audit = direct_interpretation
            if persistence:
                try:
                    save_user_understanding_audit(
                        service_account_info=persistence["service_account_info"],
                        spreadsheet_id=persistence["spreadsheet_id"],
                        spreadsheet_title=persistence["spreadsheet_title"],
                        owner_email=persistence["owner_email"],
                        run_id=str(st.session_state.run_id or ""),
                        chapter_id=_chapter_id(),
                        chapter_instance_id=str(
                            narrative_state.get("chapter_instance_id", "") or ""
                        ),
                        chapter_turn=current_turn_number,
                        row=direct_row,
                        user_text=(
                            "Prosseguir [controle automático]"
                            if automatic_direct_turn
                            else "\n".join(
                                part for part in [
                                    f"[DIREÇÃO/ENCENAÇÃO] {scene_direction}" if scene_direction else "",
                                    f"[FALA] {dialogue_text}" if dialogue_text else "",
                                ] if part
                            )
                        ),
                        previous_mary_text=previous_mary_text,
                        audit=understanding_audit,
                    )
                except Exception as understanding_audit_exc:
                    st.session_state.audit_error = str(understanding_audit_exc)

            current_chapter_prompt = build_direct_writer_prompt(
                row=direct_row,
                all_rows=direct_rows,
                recent_messages=messages_before_turn,
                user_text=("Prosseguir" if automatic_direct_turn else dialogue_text),
                user_scene_direction=("" if mary_first_turn else scene_direction),
                interpretation=direct_interpretation,
                previous_mary_text=previous_mary_text,
                previous_conversation_state=previous_conversation_state,
                active_interlocutor=active_interlocutor,
                character_name=str(
                    scene_for_director.get("temporary_character", {}).get("name", "") or ""
                ),
                handoff_text=direct_handoff_text,
            )
            current_chapter_prompt += "\n\n" + HUMANIZER_INTERPRETATIVO

        elif script_mode == "block_sheet":
            current_chapter_prompt = build_block_prompt(
                facts_prompt=str(chapter_config.get("facts_prompt", "") or ""),
                row=block_row,
                state=block_state or {},
                scene=scene_for_director,
            )
        elif script_mode == "funnel_sheet":
            current_chapter_prompt = build_funnel_prompt(
                facts_prompt=str(chapter_config.get("facts_prompt", "") or ""),
                row=funnel_row,
                state=funnel_state or {},
                scene=scene_for_director,
            )
        elif script_mode == "hybrid_phase_sheet":
            current_chapter_prompt = build_carona_prompt(
                facts_prompt=str(chapter_config.get("facts_prompt", "") or ""),
                phase=current_phase,
                row=hybrid_selected_row,
                state=hybrid_state or {},
                character_name=str(
                    scene_for_director.get("temporary_character", {}).get("name", "") or ""
                ),
                continuity_text=hybrid_continuity,
                closing_convergence_text=closing_convergence_prompt(
                    state=hybrid_state or {},
                    phase=current_phase,
                    chapter_turn=current_turn_number,
                    after_turns=int(chapter_config.get("convergence_after_turns", 14) or 14),
                ),
            )
        else:
            current_chapter_prompt = chapter_prompt(
                _chapter_id(),
                turn_number=current_turn_number,
            )

        if not director_chapter_prompt:
            director_chapter_prompt = current_chapter_prompt

        if script_mode == "direct_sheet":
            director_context_messages = phase_messages[-1:] if user_spoke else []
        elif script_mode == "block_sheet":
            # No motor de blocos, a memória recente autoral substitui o histórico bruto.
            # O Diretor recebe somente a fala atual para não canonizar erros antigos.
            director_context_messages = phase_messages[-1:] if user_spoke else []
        elif script_mode == "funnel_sheet":
            director_context_messages = compact_context_messages(
                phase_messages,
                limit=8,
            )
        else:
            director_context_messages = phase_messages

        if script_mode == "direct_sheet":
            # No roteiro direto, a planilha fornece o estado local e as memórias
            # autorais; o runtime preserva a sequência e o Redator interpreta a linha.
            scene = deepcopy(scene_for_director)
            scene["mary_immediate_goal"] = ""
            scene["mary_action"] = ""
            scene["event"] = str(
                direct_row.get("instant_memory", "") if direct_row else ""
            ).strip()
            scene["scene_changed"] = False
            director_audit = {}
        else:
            scene = direct_scene(
                api_key=api_key,
                model=director_model,
                fallback_model=fallback,
                physical_canon=PHYSICAL_CANON,
                story_ledger=story_ledger_text(st.session_state.story_state),
                current_status=current_status_text(st.session_state.story_state),
                current_scene=scene_for_director,
                user_role=user_role,
                recent_messages=director_context_messages,
                scene_direction=scene_direction,
                user_spoke=user_spoke,
                chapter_text=director_chapter_prompt,
                funnel_mode=(script_mode in {"funnel_sheet", "block_sheet"}),
                conditional_transition=(
                    False
                    if script_mode in {"hybrid_phase_sheet", "funnel_sheet", "block_sheet"}
                    else (
                        str(chapter_config.get("transition", "")) == "auto_condition"
                        or (
                            bool(str(chapter_config.get("choice_ready_when", "") or "").strip())
                            and current_turn_number
                            >= int(chapter_config.get("decision_after_turns", 0) or 0)
                        )
                    )
                ),
                advance_when=(
                    ""
                    if script_mode in {"hybrid_phase_sheet", "funnel_sheet", "block_sheet"}
                    else (
                        str(chapter_config.get("advance_when", "") or "")
                        if str(chapter_config.get("transition", "")) == "auto_condition"
                        else str(chapter_config.get("choice_ready_when", "") or "")
                    )
                ),
            )
            director_audit = scene.pop("_director_audit", {})

        # Na Carona híbrida, a cena física atualizada pelo Diretor pode liberar
        # uma linha que ainda não estava disponível antes deste turno.
        if script_mode == "hybrid_phase_sheet":
            current_phase, hybrid_selected_row, hybrid_continuity = select_carona_line(
                hybrid_rows,
                hybrid_state or {},
                scene,
            )
            current_phase_id = str(current_phase.get("id", "") or "").strip()
            current_phase_goal = str(current_phase.get("goal", "") or "").strip()
            hybrid_closing_convergence = closing_convergence_prompt(
                state=hybrid_state or {},
                phase=current_phase,
                chapter_turn=current_turn_number,
                after_turns=int(chapter_config.get("convergence_after_turns", 14) or 14),
            )
            current_chapter_prompt = build_carona_prompt(
                facts_prompt=str(chapter_config.get("facts_prompt", "") or ""),
                phase=current_phase,
                row=hybrid_selected_row,
                state=hybrid_state or {},
                character_name=str(
                    scene.get("temporary_character", {}).get("name", "") or ""
                ),
                continuity_text=hybrid_continuity,
                closing_convergence_text=hybrid_closing_convergence,
            )

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
            skip_terms = [
                str(item or "").strip().lower()
                for item in current_phase.get("entry_caption_skip_if_recent", [])
                if str(item or "").strip()
            ]
            recent_world_text = " ".join(
                [
                    str(st.session_state.scene_state.get("event", "") or ""),
                    str(st.session_state.scene_state.get("scene_caption", "") or ""),
                    str(scene_direction or ""),
                    str(dialogue_text or ""),
                    *[
                        str(record.get("user_text", "") or "")
                        + " "
                        + str(record.get("direction", "") or "")
                        + " "
                        + str(record.get("caption", "") or "")
                        for record in st.session_state.turn_records[-2:]
                    ],
                ]
            ).lower()
            caption_already_established = bool(
                skip_terms
                and any(term in recent_world_text for term in skip_terms)
            )
            if phase_entry_caption and not caption_already_established:
                scene["show_caption"] = True
                scene["scene_caption"] = phase_entry_caption

        narrative_for_opening = st.session_state.story_state.get("narrative", {})
        if narrative_for_opening.get("chapter_opening_pending"):
            opening_caption = str(
                _runtime_get_chapter(_chapter_id()).get("opening_caption", "") or ""
            ).strip()
            if opening_caption:
                scene["show_caption"] = True
                scene["scene_caption"] = opening_caption

        if script_mode == "direct_sheet" and current_turn_number > 1:
            scene["show_caption"] = False
            scene["scene_caption"] = ""

        scene_text = json.dumps(scene, ensure_ascii=False)
        if script_mode == "direct_sheet":
            # O Redator recebe diretamente a linha autoral da planilha.
            system_prompt = current_chapter_prompt
        else:
            system_prompt = build_system_prompt(
                physical_canon=PHYSICAL_CANON,
                story_ledger=story_ledger_text(st.session_state.story_state),
                current_status=current_status_text(st.session_state.story_state),
                chapter_text=current_chapter_prompt,
                scene_text=scene_text,
                user_role=user_role,
                handoff_text=_handoff_text(st.session_state.story_state),
            )

        if script_mode == "direct_sheet":
            # A fala atual já está dentro do prompt direto; não envie histórico paralelo.
            context_messages = []
        elif script_mode == "block_sheet":
            # O bloco traz memória recente autoral explícita; não reenvia o histórico bruto.
            context_messages = phase_messages[-1:] if user_spoke else []
        elif script_mode == "funnel_sheet":
            context_messages = compact_context_messages(
                phase_messages,
                limit=8,
            )
        else:
            context_messages = phase_messages[-24:]
        llm_messages = [
            {"role": "system", "content": system_prompt},
            *(
                [
                    {
                        "role": "system",
                        "content": (
                            "GUARDRAILS DO RUNTIME: preserve fatos duros, identidade, papel, posse e posição física. "
                            "Responda ao sentido da conversa real antes de tentar desenvolver a linha ativa. "
                            "Não espelhe pergunta, provocação ou comando do usuário como resposta. "
                            "Não execute linhas futuras. Não transforme erros do modelo em fatos narrativos. "
                            "Nunca mencione prompt, roteiro, fala-guia, modelo, Diretor, memória ou instruções internas."
                        ),
                    }
                ]
                if script_mode == "direct_sheet"
                else []
            ),
            *context_messages,
        ]
        model_audit = {
            "model": model,
            "fallback_model": fallback or "",
            "temperature": temperature,
            "system_prompt": system_prompt,
            "messages": deepcopy(llm_messages),
            "initial_raw_response": "",
            "retry_used": False,
            "retry_messages": [],
            "retry_raw_response": "",
            "final_raw_response": "",
            "mary_speech_raw": "",
            "mary_thought": "",
            "final_mary_text": "",
            "funnel_evaluation_initial": {},
            "funnel_evaluation_final": {},
        }

        thought_disabled = script_mode == "direct_sheet" and is_direct_thought_disabled(direct_row)
        try:
            raw_answer = chat(
                api_key=api_key,
                model=model,
                fallback_model=fallback,
                messages=llm_messages,
                temperature=temperature,
            )
            model_audit["initial_raw_response"] = raw_answer
            mary_intent, mary_speech_raw = _parse_direct_flexible_response(raw_answer, script_mode, thought_disabled=thought_disabled)
            narration_leak = looks_like_action_narration(mary_speech_raw)
            answer = sanitize_mary_output(mary_speech_raw)

            if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                retry_messages = [
                    *llm_messages,
                    {
                        "role": "system",
                        "content": (
                            "CORREÇÃO DE FORMATO: no roteiro direto use apenas os blocos necessários: "
                            "[AÇÃO] para movimento executado, [FALA] para diálogo e "
                            "[PENSAMENTO] opcional para experiência interior, sem obrigação de ação ou fala correspondente. "
                            "Não coloque ações entre asteriscos dentro da fala."
                        ),
                    },
                ]
                model_audit["retry_used"] = True
                model_audit["retry_messages"] = deepcopy(retry_messages)
                raw_answer = chat(
                    api_key=api_key,
                    model=model,
                    fallback_model=fallback,
                    messages=retry_messages,
                    temperature=max(0.2, min(float(temperature), 0.8)),
                )
                model_audit["retry_raw_response"] = raw_answer
                mary_intent, mary_speech_raw = _parse_direct_flexible_response(raw_answer, script_mode, thought_disabled=thought_disabled)
                narration_leak = looks_like_action_narration(mary_speech_raw)
                answer = sanitize_mary_output(mary_speech_raw)

            if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                raise OpenRouterError(
                    "O modelo não produziu fala verbal limpa de Mary após duas tentativas."
                )

            if (
                script_mode == "direct_sheet"
                and direct_state is not None
                and direct_row
            ):
                direct_validation = validate_direct_semantic_turn(
                    api_key=api_key,
                    model=director_model,
                    fallback_model=fallback,
                    row=direct_row,
                    interpretation=direct_interpretation,
                    mary_text=answer,
                    mary_thought=mary_intent, mary_action=parse_mary_components(raw_answer)["action"],
                    user_text=dialogue_text,
                    user_scene_direction=scene_direction,
                    line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                )

                parsed_objectives = (
                    direct_validation.get("parsed_response", {}).get("objetivos_guia", [])
                    if isinstance(direct_validation.get("parsed_response", {}), dict)
                    else []
                )
                normalized_objectives = direct_validation.get("elements", [])
                claimed_without_real_evidence = any(
                    isinstance(raw_item, dict)
                    and bool(raw_item.get("alcancado", False))
                    and (
                        idx >= len(normalized_objectives)
                        or (
                            not bool(
                                (normalized_objectives[idx] or {}).get("optional", False)
                            )
                            and not str(
                                (normalized_objectives[idx] or {}).get("evidence", "") or ""
                            ).strip()
                        )
                    )
                    for idx, raw_item in enumerate(parsed_objectives or [])
                )

                thought_check_missing = (
                    bool(str(direct_row.get("thought_guide", "") or "").strip())
                    and bool(str(mary_intent or "").strip())
                    and "pensamento_autoral" not in (
                        direct_validation.get("parsed_response", {}) or {}
                    )
                )
                if (
                    str(direct_validation.get("parse_error", "") or "").strip()
                    or bool(direct_validation.get("invalid_guide_evidence", False))
                    or claimed_without_real_evidence
                    or thought_check_missing
                ):
                    # Falha técnica ou evidência sem apoio real na conversa
                    # não deve prolongar artificialmente a linha.
                    # Repete somente a validação; a fala de Mary não é regenerada.
                    direct_validation = validate_direct_semantic_turn(
                        api_key=api_key,
                        model=director_model,
                        fallback_model=fallback,
                        row=direct_row,
                        interpretation=direct_interpretation,
                        mary_text=answer,
                        mary_thought=mary_intent, mary_action=parse_mary_components(raw_answer)["action"],
                        user_text=dialogue_text,
                        user_scene_direction=scene_direction,
                        line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                    )

                if (
                    str(direct_row.get("thought_guide", "") or "").strip()
                    and str(mary_intent or "").strip()
                    and "pensamento_autoral" not in (
                        direct_validation.get("parsed_response", {}) or {}
                    )
                ):
                    raise OpenRouterError(
                        "O Diretor não devolveu a avaliação do PENSAMENTO-GUIA após duas tentativas."
                    )

                if str(direct_validation.get("parse_error", "") or "").strip():
                    # Falha técnica do Diretor não vira estado narrativo.
                    # O bloco try externo restaura integralmente o turno.
                    raise OpenRouterError(
                        "O Diretor semântico não devolveu validação estruturada após duas tentativas."
                    )

                conversation_consistency = direct_validation.get(
                    "conversation_consistency", {}
                )
                if (
                    isinstance(conversation_consistency, dict)
                    and not bool(conversation_consistency.get("ok", True))
                ):
                    model_audit["direct_validation_before_conversation_correction"] = deepcopy(
                        direct_validation
                    )
                    conversation_retry_messages = [
                        *llm_messages,
                        {
                            "role": "system",
                            "content": (
                                "CORREÇÃO DE CONTINUIDADE OBRIGATÓRIA. A resposta anterior não respeitou "
                                "o movimento conversacional compreendido do usuário. Reescreva a resposta "
                                "preservando sujeito, destinatário, autoria da iniciativa, vocativos, posse "
                                "e a relação causal com o turno anterior. Não explique o erro e não invente "
                                "uma justificativa narrativa para ele. NÃO force a fala-guia se ela ainda "
                                "não couber naturalmente. Problema: "
                                + str(conversation_consistency.get("issue", "") or "")
                                + ". Trecho problemático: "
                                + str(conversation_consistency.get("mary_excerpt", "") or "")
                                + ". Correção semântica esperada: "
                                + str(conversation_consistency.get("correction", "") or "")
                                + ". Preserve os blocos [AÇÃO], [FALA] e [PENSAMENTO] quando necessários."
                            ),
                        },
                    ]
                    raw_answer = chat(
                        api_key=api_key,
                        model=model,
                        fallback_model=fallback,
                        messages=conversation_retry_messages,
                        temperature=max(0.2, min(float(temperature), 0.7)),
                    )
                    model_audit["retry_used"] = True
                    model_audit["retry_messages"] = deepcopy(conversation_retry_messages)
                    model_audit["retry_raw_response"] = raw_answer
                    mary_intent, mary_speech_raw = _parse_direct_flexible_response(raw_answer, script_mode, thought_disabled=thought_disabled)
                    narration_leak = looks_like_action_narration(mary_speech_raw)
                    answer = sanitize_mary_output(mary_speech_raw)
                    if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                        raise OpenRouterError(
                            "A correção de continuidade não produziu fala verbal limpa de Mary."
                        )
                    direct_validation = validate_direct_semantic_turn(
                        api_key=api_key,
                        model=director_model,
                        fallback_model=fallback,
                        row=direct_row,
                        interpretation=direct_interpretation,
                        mary_text=answer,
                        mary_thought=mary_intent, mary_action=parse_mary_components(raw_answer)["action"],
                        user_text=dialogue_text,
                        user_scene_direction=scene_direction,
                        line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                    )
                    if not bool(
                        (direct_validation.get("conversation_consistency", {}) or {}).get(
                            "ok", True
                        )
                    ):
                        raise OpenRouterError(
                            "A resposta de Mary manteve incoerência conversacional após correção."
                        )

                naturalness = direct_validation.get("naturalness", {})
                if isinstance(naturalness, dict) and naturalness.get("ok") is False:
                    model_audit["direct_validation_before_style_correction"] = deepcopy(direct_validation)
                    style_retry_messages = [
                        *llm_messages,
                        {"role": "assistant", "content": raw_answer},
                        {"role": "system", "content": (
                            "REESCRITA DE EXPRESSÃO NATURAL: mantenha os mesmos acontecimentos, "
                            "fatos, interlocutores, limites, personalidade e objetivo desta linha. "
                            "Corrija SOMENTE os canais afetados pelo problema indicado. "
                            "Se for excesso em [AÇÃO], remova apenas gestos, sensações e "
                            "enfeites sem função, preservando integralmente as ações obrigatórias. "
                            "Se for [FALA], use português brasileiro cotidiano e reação específica; "
                            "não altere [PENSAMENTO] quando não houver problema nele. "
                            "Problema: " + str(naturalness.get("issue", "") or "") +
                            ". Trecho: " + str(naturalness.get("mary_excerpt", "") or "") +
                            ". Ajuste: " + str(naturalness.get("correction", "") or "") +
                            ". Retorne apenas os blocos necessários [AÇÃO], [FALA], [PENSAMENTO]."
                        )},
                    ]
                    style_raw = chat(
                        api_key=api_key, model=model, fallback_model=fallback,
                        messages=style_retry_messages,
                        temperature=max(0.2, min(float(temperature), 0.7)),
                    )
                    style_thought, style_speech = _parse_direct_flexible_response(style_raw, script_mode, thought_disabled=thought_disabled)
                    style_answer = sanitize_mary_output(style_speech)
                    if (style_answer or parse_mary_components(style_raw)["action"]) and not looks_like_action_narration(style_speech):
                        style_validation = validate_direct_semantic_turn(
                            api_key=api_key, model=director_model,
                            fallback_model=fallback, row=direct_row,
                            interpretation=direct_interpretation,
                            mary_text=style_answer, mary_thought=style_thought, mary_action=parse_mary_components(style_raw)["action"],
                            user_text=dialogue_text, user_scene_direction=scene_direction,
                            line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                        )
                        if (
                            bool(style_validation.get("fulfilled", False))
                            and not str(style_validation.get("parse_error", "") or "").strip()
                        ):
                            raw_answer = style_raw
                            mary_intent, mary_speech_raw = style_thought, style_speech
                            answer = style_answer
                            direct_validation = style_validation
                            model_audit["retry_used"] = True
                            model_audit["retry_messages"] = deepcopy(style_retry_messages)
                            model_audit["retry_raw_response"] = style_raw
                        else:
                            model_audit["style_retry_rejected"] = style_validation.get("reason", "")
                    else:
                        model_audit["style_retry_rejected"] = "Resposta revisada sem fala limpa."
                revelation_violation = direct_validation.get(
                    "revelation_violation", {}
                )
                if (
                    isinstance(revelation_violation, dict)
                    and bool(revelation_violation.get("exists", False))
                ):
                    model_audit["direct_validation_before_revelation_correction"] = deepcopy(
                        direct_validation
                    )
                    revelation_retry_messages = [
                        *llm_messages,
                        {
                            "role": "system",
                            "content": (
                                "CORREÇÃO DE REVELAÇÃO OBRIGATÓRIA. A resposta anterior verbalizou "
                                "conteúdo que Mary conhece, mas que ainda está reservado para uma linha futura. "
                                "Reescreva a resposta reagindo naturalmente à fala atual do usuário, sem mentir, "
                                "sem inventar fatos e sem revelar o conteúdo reservado. Se o usuário perguntou "
                                "diretamente pelo dado proibido, Mary pode hesitar, pedir um instante, dizer que vai "
                                "contar ou preparar a revelação, mas não pode entregá-la ainda. Preserve a FALA-GUIA "
                                "da linha atual somente até onde ela couber naturalmente. "
                                "Regra da linha: "
                                + str(direct_row.get("revelation_policy", "") or "")
                                + ". Conteúdo reservado detectado: "
                                + str(revelation_violation.get("reserved_content", "") or "")
                                + ". Trecho problemático: "
                                + str(revelation_violation.get("mary_excerpt", "") or "")
                                + ". Correção esperada: "
                                + str(revelation_violation.get("correction", "") or "")
                                + ". Preserve os blocos [AÇÃO], [FALA] e [PENSAMENTO] quando necessários."
                            ),
                        },
                    ]
                    raw_answer = chat(
                        api_key=api_key,
                        model=model,
                        fallback_model=fallback,
                        messages=revelation_retry_messages,
                        temperature=max(0.2, min(float(temperature), 0.7)),
                    )
                    model_audit["retry_used"] = True
                    model_audit["retry_messages"] = deepcopy(revelation_retry_messages)
                    model_audit["retry_raw_response"] = raw_answer
                    mary_intent, mary_speech_raw = _parse_direct_flexible_response(raw_answer, script_mode, thought_disabled=thought_disabled)
                    narration_leak = looks_like_action_narration(mary_speech_raw)
                    answer = sanitize_mary_output(mary_speech_raw)
                    if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                        raise OpenRouterError(
                            "A correção de revelação não produziu fala verbal limpa de Mary."
                        )
                    direct_validation = validate_direct_semantic_turn(
                        api_key=api_key,
                        model=director_model,
                        fallback_model=fallback,
                        row=direct_row,
                        interpretation=direct_interpretation,
                        mary_text=answer,
                        mary_thought=mary_intent, mary_action=parse_mary_components(raw_answer)["action"],
                        user_text=dialogue_text,
                        user_scene_direction=scene_direction,
                        line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                    )
                    if bool(
                        (direct_validation.get("revelation_violation", {}) or {}).get(
                            "exists", False
                        )
                    ):
                        raise OpenRouterError(
                            "A resposta de Mary manteve antecipação de revelação após correção."
                        )

                hard_contradiction = direct_validation.get("hard_contradiction", {})
                if (
                    isinstance(hard_contradiction, dict)
                    and bool(hard_contradiction.get("exists", False))
                ):
                    model_audit["direct_validation_before_factual_correction"] = deepcopy(
                        direct_validation
                    )
                    factual_retry_messages = [
                        *llm_messages,
                        {
                            "role": "system",
                            "content": (
                                "CORREÇÃO FACTUAL OBRIGATÓRIA. A resposta anterior contradisse "
                                "uma fonte autoritativa. Reescreva somente o necessário para restaurar "
                                "a verdade factual e preservar a reação natural ao usuário. "
                                "NÃO force a fala-guia se ela ainda não couber naturalmente. "
                                "Se o usuário percebeu ou questionou o erro, Mary pode reconhecer "
                                "o lapso de forma breve e humana. "
                                "Fato autoritativo: "
                                + str(hard_contradiction.get("authoritative_fact", "") or "")
                                + ". Trecho contraditório: "
                                + str(hard_contradiction.get("mary_excerpt", "") or "")
                                + ". Correção: "
                                + str(hard_contradiction.get("correction", "") or "")
                                + ". Preserve os blocos [AÇÃO], [FALA] e [PENSAMENTO] quando necessários."
                            ),
                        },
                    ]
                    raw_answer = chat(
                        api_key=api_key,
                        model=model,
                        fallback_model=fallback,
                        messages=factual_retry_messages,
                        temperature=max(0.2, min(float(temperature), 0.7)),
                    )
                    model_audit["retry_used"] = True
                    model_audit["retry_messages"] = deepcopy(factual_retry_messages)
                    model_audit["retry_raw_response"] = raw_answer
                    mary_intent, mary_speech_raw = _parse_direct_flexible_response(raw_answer, script_mode, thought_disabled=thought_disabled)
                    narration_leak = looks_like_action_narration(mary_speech_raw)
                    answer = sanitize_mary_output(mary_speech_raw)
                    if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                        raise OpenRouterError(
                            "A correção factual não produziu fala verbal limpa de Mary."
                        )
                    direct_validation = validate_direct_semantic_turn(
                        api_key=api_key,
                        model=director_model,
                        fallback_model=fallback,
                        row=direct_row,
                        interpretation=direct_interpretation,
                        mary_text=answer,
                        mary_thought=mary_intent, mary_action=parse_mary_components(raw_answer)["action"],
                        user_text=dialogue_text,
                        user_scene_direction=scene_direction,
                        line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                    )
                    if bool(
                        (direct_validation.get("hard_contradiction", {}) or {}).get(
                            "exists", False
                        )
                    ):
                        raise OpenRouterError(
                            "A resposta de Mary manteve contradição factual após correção."
                        )
                # Uma unica reescrita da cena incompleta, sem repetir orientacoes
                # de comportamento nem permitir que o roteiro prove a si proprio.
                scene_check = direct_validation.get("scene_completion", {})
                if isinstance(scene_check, dict) and scene_check.get("fulfilled") is False:
                    model_audit["direct_validation_before_scene_correction"] = deepcopy(direct_validation)
                    scene_retry_messages = [
                        *llm_messages,
                        {"role": "assistant", "content": raw_answer},
                        {"role": "system", "content": (
                            "A LINHA AINDA NAO TERMINOU. O acontecimento obrigatorio nao "
                            "foi demonstrado pela resposta anterior. Nao repita despedidas, "
                            "promessas de ir ou pedidos ja aceitos. Mostre a acao efetiva "
                            "agora no bloco [AÇÃO], se for um movimento silencioso, "
                            "e mantenha [FALA] apenas "
                            "se houver algo relevante a dizer. Diferencie a acao ja feita "
                            "da intencao de faze-la. Fato faltante: "
                            + str(scene_check.get("missing", "") or scene_check.get("event", "") or "")
                            + ". Preserve o local, a sequencia e os personagens atuais. "
                            "Use [AÇÃO], [FALA] ou [PENSAMENTO] conforme necessário, sem antecipar outras linhas."
                        )},
                    ]
                    scene_raw = chat(
                        api_key=api_key, model=model, fallback_model=fallback,
                        messages=scene_retry_messages,
                        temperature=max(0.2, min(float(temperature), 0.7)),
                    )
                    scene_thought, scene_speech = _parse_direct_flexible_response(scene_raw, script_mode, thought_disabled=thought_disabled)
                    scene_answer = sanitize_mary_output(scene_speech)
                    if (scene_answer or parse_mary_components(scene_raw)["action"]) and not looks_like_action_narration(scene_speech):
                        scene_validation = validate_direct_semantic_turn(
                            api_key=api_key, model=director_model,
                            fallback_model=fallback, row=direct_row,
                            interpretation=direct_interpretation,
                            mary_text=scene_answer, mary_thought=scene_thought, mary_action=parse_mary_components(scene_raw)["action"],
                            user_text=dialogue_text, user_scene_direction=scene_direction,
                            line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                        )
                        if bool(scene_validation.get("fulfilled", False)):
                            raw_answer = scene_raw
                            mary_intent, mary_speech_raw = scene_thought, scene_speech
                            answer = scene_answer
                            direct_validation = scene_validation
                            model_audit["retry_used"] = True
                            model_audit["retry_messages"] = deepcopy(scene_retry_messages)
                            model_audit["retry_raw_response"] = scene_raw
                        else:
                            model_audit["scene_retry_rejected"] = deepcopy(scene_validation.get("scene_completion", {}))
                    else:
                        model_audit["scene_retry_rejected"] = "Saida sem fala valida."

                # Linhas automáticas são atômicas: nenhuma resposta pendente
                # pode chegar à tela, à persistência ou consumir outro clique.
                if automatic_turn and not bool(direct_validation.get("fulfilled", False)):
                    auto_retry_messages = [
                        *llm_messages,
                        {"role": "assistant", "content": raw_answer},
                        {"role": "system", "content": (
                            "CORREÇÃO INTERNA DA LINHA AUTOMÁTICA. A tentativa anterior "
                            "não concluiu o objetivo autoral: "
                            + str(direct_validation.get("missing", "") or "objetivo incompleto")
                            + ". Gere uma resposta efetivamente corrigida, sem repetir a anterior. "
                            "Execute apenas a linha atual, respeitando contexto e limites. "
                            "Use os blocos [AÇÃO], [FALA], [PENSAMENTO] quando pertinentes."
                        )},
                    ]
                    auto_raw = chat(
                        api_key=api_key, model=model, fallback_model=fallback,
                        messages=auto_retry_messages, temperature=temperature,
                    )
                    auto_parts = parse_mary_components(auto_raw)
                    auto_speech = sanitize_mary_output(auto_parts["speech"])
                    if (not auto_speech and not auto_parts["action"]) or looks_like_action_narration(auto_speech):
                        raise OpenRouterError(
                            "Linha automática sem resposta válida após correção interna; nada foi publicado."
                        )
                    auto_validation = validate_direct_semantic_turn(
                        api_key=api_key, model=director_model, fallback_model=fallback,
                        row=direct_row, interpretation=direct_interpretation,
                        mary_text=auto_speech, mary_thought=("" if thought_disabled else auto_parts["thought"]),
                        mary_action=auto_parts["action"], user_text=dialogue_text,
                        user_scene_direction=scene_direction,
                        line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                    )
                    if (
                        not bool(auto_validation.get("fulfilled", False))
                        or str(auto_validation.get("parse_error", "") or "").strip()
                    ):
                        # Segunda tentativa com os motivos da reprovação atual.
                        # Não publica respostas sem aprovação do Diretor.
                        missing_detail = str(auto_validation.get("missing", "") or "").strip()
                        scene_detail = auto_validation.get("scene_completion", {}) or {}
                        correction_messages = [
                            *llm_messages,
                            {"role": "assistant", "content": auto_raw},
                            {"role": "system", "content": (
                                "ÚLTIMA CORREÇÃO DA LINHA AUTOMÁTICA. O Diretor reprovou "
                                "a tentativa anterior. Falha: "
                                + (missing_detail or str(scene_detail.get("missing", "") or "objetivo não comprovado"))
                                + ". Execute estritamente a Descrição-guia, a Fala-guia e "
                                "o Pensamento-guia da LINHA ATIVA, sem repetir frases da tentativa "
                                "anterior, sem antecipar linhas futuras. A ação física deve estar "
                                "explicitamente descrita em [AÇÃO] e a fala verbal em [FALA]. "
                                "Use evidências concretas, não apenas intenções."
                            )},
                        ]
                        last_raw = chat(
                            api_key=api_key, model=model, fallback_model=fallback,
                            messages=correction_messages,
                            temperature=max(0.2, min(float(temperature), 0.5)),
                        )
                        last_parts = parse_mary_components(last_raw)
                        last_speech = sanitize_mary_output(last_parts["speech"])
                        if (last_speech or last_parts["action"]) and not looks_like_action_narration(last_speech):
                            last_validation = validate_direct_semantic_turn(
                                api_key=api_key, model=director_model, fallback_model=fallback,
                                row=direct_row, interpretation=direct_interpretation,
                                mary_text=last_speech, mary_thought=("" if thought_disabled else last_parts["thought"]),
                                mary_action=last_parts["action"], user_text=dialogue_text,
                                user_scene_direction=scene_direction,
                                line_dialogue=list(direct_state.get("line_dialogue", []) or []),
                            )
                            # Registrar a avaliação MAIS RECENTE mesmo quando a
                            # última correção não resolver o problema; o erro anterior
                            # não pode mascarar a verdadeira causa de rejeição.
                            auto_validation = last_validation
                            if bool(last_validation.get("fulfilled", False)) and not last_validation.get("parse_error"):
                                auto_raw, auto_parts, auto_speech = (
                                    last_raw, last_parts, last_speech
                                )
                        if not bool(auto_validation.get("fulfilled", False)) or auto_validation.get("parse_error"):
                            # Uma falha de execução não vira interação, mas DEVE
                            # ser auditável para diagnosticar a linha sem adivinhar.
                            if persistence:
                                try:
                                    save_director_validation_audit(
                                        service_account_info=persistence["service_account_info"],
                                        spreadsheet_id=persistence["spreadsheet_id"],
                                        spreadsheet_title=persistence["spreadsheet_title"],
                                        owner_email=persistence["owner_email"],
                                        run_id=str(st.session_state.run_id or ""),
                                        seq_candidate=int(st.session_state.run_last_seq or 0) + 1,
                                        chapter_id=_chapter_id(),
                                        chapter_instance_id=str(narrative_state.get("chapter_instance_id", "") or ""),
                                        chapter_turn=current_turn_number,
                                        row=direct_row,
                                        user_text=dialogue_text,
                                        attempt=3,
                                        mary_text=last_speech,
                                        evaluation=auto_validation,
                                        status="AUTO_REJECTED_NOT_PUBLISHED",
                                    )
                                except Exception as rejected_audit_exc:
                                    _LOG.warning("Falha ao auditar linha automática rejeitada: %s", rejected_audit_exc)
                            scene_detail = auto_validation.get("scene_completion", {}) or {}
                            _LOG.warning(
                                "AUTO_LINE_VALIDATION_REJECTED chapter=%s line=%s missing=%s scene=%s parse=%s",
                                str(narrative_state.get("chapter_id", "")),
                                str(direct_row.get("order", "")),
                                str(auto_validation.get("missing", ""))[:400],
                                str(scene_detail.get("missing", ""))[:300],
                                str(auto_validation.get("parse_error", ""))[:160],
                            )
                            raise OpenRouterError(
                                "Linha automática não aprovada após correções internas. "
                                "Nenhuma resposta foi exibida ou salva. Consulte o log "
                                "AUTO_LINE_VALIDATION_REJECTED e tente Prosseguir novamente."
                            )
                    model_audit["retry_used"] = True
                    model_audit["retry_messages"] = deepcopy(auto_retry_messages)
                    model_audit["retry_raw_response"] = auto_raw
                    raw_answer = auto_raw
                    mary_intent = "" if thought_disabled else auto_parts["thought"]
                    mary_speech_raw = auto_parts["speech"]
                    answer = auto_speech
                    direct_validation = auto_validation

                if persistence:
                    try:
                        save_director_validation_audit(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=persistence["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=str(st.session_state.run_id or ""),
                            seq_candidate=int(st.session_state.run_last_seq or 0) + 1,
                            chapter_id=_chapter_id(),
                            chapter_instance_id=str(
                                narrative_state.get("chapter_instance_id", "") or ""
                            ),
                            chapter_turn=current_turn_number,
                            row=direct_row,
                            user_text=dialogue_text,
                            attempt=1,
                            mary_text=answer,
                            evaluation=direct_validation,
                            status=(
                                "APPROVED"
                                if bool(direct_validation.get("fulfilled", False))
                                else "PENDING_SAME_LINE"
                            ),
                        )
                    except Exception as director_validation_audit_exc:
                        st.session_state.audit_error = str(
                            director_validation_audit_exc
                        )
                director_audit = {
                    "model": direct_validation.get("model", director_model),
                    "duration_ms": direct_validation.get("duration_ms", ""),
                    "conditional_transition": False,
                    "advance_when": "",
                    "scene_before": {},
                    "input_payload": direct_validation.get("input_payload", ""),
                    "raw_response": direct_validation.get("raw_response", ""),
                    "parsed_response": direct_validation.get("parsed_response", {}),
                    "parse_error": direct_validation.get("parse_error", ""),
                    "scene_after": {
                        "validation_mode": "direct_line_completion",
                        "fulfilled": bool(direct_validation.get("fulfilled", False)),
                        "missing": str(direct_validation.get("missing", "") or ""),
                        "reason": str(direct_validation.get("reason", "") or ""),
                    },
                }

                if not bool(direct_validation.get("fulfilled", False)):
                    # A linha direta pode levar mais de uma interação.
                    # Preserve a fala atual de Mary e mantenha a mesma missão ativa.
                    # O próximo turno continua na mesma linha até a validação semântica fechar.
                    director_audit.setdefault("scene_after", {})["pending_same_line"] = True

                # Interpreta semanticamente o movimento que a própria Mary acabou de criar.
                # Esse estado, e não apenas o texto bruto, será a âncora causal do próximo turno.
                mary_conversation_state = analyze_mary_move(
                    api_key=api_key,
                    model=director_model,
                    fallback_model=fallback,
                    mary_text=answer,
                    user_text=dialogue_text,
                    user_understanding=direct_interpretation,
                    previous_conversation_state=previous_conversation_state,
                    active_interlocutor=active_interlocutor,
                )
                narrative_state["direct_conversation_state"] = mary_conversation_state

                # Guarda a conversa específica desta linha para que o Diretor possa
                # reconhecer objetivos já satisfeitos pelo próprio usuário em turnos seguintes.
                if str(direct_row.get("line_id", "") or "") != "loop_orgulho_ferido":
                    record_direct_line_turn(
                        direct_state,
                        user_text=dialogue_text,
                        mary_text=answer,
                    )

            if (
                script_mode == "funnel_sheet"
                and funnel_state is not None
                and funnel_row
            ):
                funnel_evaluation = evaluate_funnel_turn(
                    api_key=api_key,
                    model=director_model,
                    fallback_model=fallback,
                    row=funnel_row,
                    state=funnel_state,
                    scene=scene,
                    user_text=dialogue_text,
                    mary_text=answer,
                    mary_thought=mary_intent,
                )
                model_audit[
                    "funnel_evaluation_initial"
                ] = deepcopy(funnel_evaluation)
                initial_funnel_mary_text = answer

                if (
                    not bool(
                        funnel_evaluation.get(
                            "boundary_ok",
                            True,
                        )
                    )
                    or not bool(
                        funnel_evaluation.get(
                            "mission_progress_ok",
                            True,
                        )
                    )
                ):
                    funnel_correction_prompt = correction_prompt(
                        funnel_row,
                        funnel_evaluation,
                        state=funnel_state,
                        scene=scene,
                    )
                    retry_messages = [
                        *llm_messages,
                        {
                            "role": "system",
                            "content": funnel_correction_prompt,
                        },
                    ]
                    model_audit["retry_used"] = True
                    model_audit["retry_messages"] = deepcopy(
                        retry_messages
                    )
                    raw_answer = chat(
                        api_key=api_key,
                        model=model,
                        fallback_model=fallback,
                        messages=retry_messages,
                        temperature=max(
                            0.2,
                            min(float(temperature), 0.7),
                        ),
                    )
                    model_audit["retry_raw_response"] = raw_answer
                    mary_intent, mary_speech_raw = parse_mary_response(
                        raw_answer
                    )
                    narration_leak = looks_like_action_narration(
                        mary_speech_raw
                    )
                    answer = sanitize_mary_output(
                        mary_speech_raw
                    )
                    if (not answer and not (script_mode == "direct_sheet" and parse_mary_components(raw_answer)["action"])) or narration_leak:
                        raise OpenRouterError(
                            "A correção do funil não produziu fala verbal limpa."
                        )

                    funnel_evaluation = evaluate_funnel_turn(
                        api_key=api_key,
                        model=director_model,
                        fallback_model=fallback,
                        row=funnel_row,
                        state=funnel_state,
                        scene=scene,
                        user_text=dialogue_text,
                        mary_text=answer,
                        mary_thought=mary_intent,
                    )

                model_audit[
                    "funnel_evaluation_final"
                ] = deepcopy(funnel_evaluation)

                if not bool(
                    funnel_evaluation.get(
                        "boundary_ok",
                        True,
                    )
                ):
                    if persistence:
                        try:
                            save_funnel_rejection(
                                service_account_info=persistence["service_account_info"],
                                spreadsheet_id=persistence["spreadsheet_id"],
                                spreadsheet_title=persistence["spreadsheet_title"],
                                owner_email=persistence["owner_email"],
                                run_id=str(st.session_state.run_id or ""),
                                chapter_id=_chapter_id(),
                                row=funnel_row,
                                state=funnel_state or {},
                                user_text=dialogue_text,
                                initial_mary_text=initial_funnel_mary_text,
                                initial_evaluation=model_audit.get(
                                    "funnel_evaluation_initial",
                                    {},
                                ),
                                correction_prompt=funnel_correction_prompt,
                                retry_mary_text=answer,
                                retry_evaluation=funnel_evaluation,
                                pending_markers=pending_markers(
                                    funnel_row,
                                    funnel_state or {},
                                    scene,
                                ),
                                required_markers=required_markers(
                                    funnel_row
                                ),
                                branch_id=str(
                                    narrative_state.get("branch_id", "main")
                                    or "main"
                                ),
                                chapter_instance_id=str(
                                    narrative_state.get(
                                        "chapter_instance_id",
                                        "",
                                    )
                                    or ""
                                ),
                                chapter_turn=int(
                                    narrative_state.get(
                                        "chapter_turns",
                                        0,
                                    )
                                    or 0
                                ),
                            )
                        except Exception as rejection_audit_exc:
                            st.session_state.audit_error = str(
                                rejection_audit_exc
                            )
                    raise OpenRouterError(
                        "A resposta de Mary ultrapassou as paredes do funil após correção."
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
            if (
                script_mode == "direct_sheet"
                and direct_row
                and is_automatic_direct_row(direct_row)
            ):
                st.session_state[_direct_auto_retry_key(
                    _chapter_id(),
                    str(narrative_state.get("chapter_instance_id", "") or ""),
                    int(direct_row.get("order", 0) or 0),
                )] = True
            raise

        # A saída final pode ter sido substituída por uma correção interna.
        # Preserve a resposta bruta na auditoria, mas nunca publique ou
        # persista pensamento de uma linha que o autor desativou.
        if thought_disabled:
            mary_intent = ""

        if emotional_notice:
            st.info(emotional_notice)
        direct_action_text = parse_mary_components(raw_answer)["action"] if script_mode == "direct_sheet" else ""
        if script_mode == "direct_sheet":
            model_audit["mary_action"] = direct_action_text
        model_audit["final_raw_response"] = raw_answer
        model_audit["mary_speech_raw"] = mary_speech_raw
        model_audit["mary_thought"] = mary_intent
        model_audit["final_mary_text"] = answer

        if (
            script_mode == "direct_sheet"
            and direct_state is not None
            and direct_row
        ):
            direct_fulfilled = bool(
                isinstance(director_audit, dict)
                and director_audit.get("scene_after", {}).get("fulfilled", False)
            )
            if direct_fulfilled and str(direct_row.get("line_id", "") or "") != "loop_orgulho_ferido":
                mark_direct_line_emitted(direct_state, direct_row, direct_rows)
            if direct_fulfilled and is_automatic_direct_row(direct_row):
                st.session_state.pop(
                    _direct_auto_retry_key(
                        _chapter_id(),
                        str(narrative_state.get("chapter_instance_id", "") or ""),
                        int(direct_row.get("order", 0) or 0),
                    ),
                    None,
                )
            _LOG.info(
                "DIRECT_SCRIPT_AUDIT order=%s type=%s completion=%s fulfilled=%s awaiting=%s",
                int(direct_row.get("order", 0) or 0),
                str(direct_row.get("type", "") or ""),
                str(direct_row.get("completion_type", "") or ""),
                direct_fulfilled,
                int(direct_state.get("awaiting_reply_order", 0) or 0),
            )
        elif (
            script_mode == "block_sheet"
            and block_state is not None
            and block_row
        ):
            block_dependency = evaluate_block_dependency(
                api_key=api_key,
                model=director_model,
                fallback_model=fallback,
                row=block_row,
                user_text=dialogue_text,
            )
            block_progress = apply_block_turn(
                rows=block_rows,
                state=block_state,
                row=block_row,
                dependency=block_dependency,
                scene=scene,
            )
            _LOG.info(
                "BLOCK_AUDIT block=%s turn=%s stage=%s depends=%s dependency_ok=%s advanced=%s next=%s holding=%s",
                str(block_row.get("block_id", "") or ""),
                int(
                    block_progress.get("state_after", {}).get(
                        "block_turn",
                        0,
                    )
                    or 0
                ),
                str(block_progress.get("stage", "") or ""),
                bool(block_row.get("depends_on_user", False)),
                bool(block_progress.get("dependency_satisfied", False)),
                bool(block_progress.get("advanced", False)),
                str(block_progress.get("advanced_to", "") or ""),
                bool(block_progress.get("holding_for_next_block", False)),
            )
        elif (
            script_mode == "funnel_sheet"
            and funnel_state is not None
            and funnel_row
        ):
            funnel_progress = apply_funnel_evaluation(
                rows=funnel_rows,
                state=funnel_state,
                row=funnel_row,
                evaluation=funnel_evaluation,
                scene=scene,
            )
            _LOG.info(
                "FUNNEL_AUDIT scene=%s turn=%s stage=%s boundary_ok=%s pending=%s advanced=%s next=%s",
                str(funnel_row.get("scene_id", "") or ""),
                int(
                    funnel_progress.get("state_after", {}).get(
                        "scene_turn",
                        0,
                    )
                    or 0
                ),
                str(funnel_progress.get("stage", "") or ""),
                bool(funnel_evaluation.get("boundary_ok", True)),
                ",".join(funnel_progress.get("pending_markers", []) or []),
                bool(funnel_progress.get("advanced", False)),
                str(funnel_progress.get("advanced_to", "") or ""),
            )

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

        active_chapter = _runtime_get_chapter(_chapter_id())

        if script_mode == "direct_sheet" and direct_state is not None:
            loop_after = narrative.get("direct_hurt_loop", {})
            if isinstance(loop_after, dict) and loop_after.get("exhausted"):
                narrative["direct_emotional_ending_blocked"] = True
                narrative["choice_ready"] = False
            elif isinstance(loop_after, dict) and loop_after.get("active"):
                narrative["choice_ready"] = False
            elif direct_script_ready_for_choice(direct_state):
                emotion_end = narrative.get("direct_emotion", {})
                forbidden = (
                    isinstance(emotion_end, dict)
                    and emotion_end.get("chapter_id") == str(narrative.get("chapter_id", "") or "")
                    and emotion_end.get("hurt") is True
                    and (
                        emotion_end.get("rejected") is True
                        or emotion_end.get("continuation_allowed") is not True
                    )
                )
                narrative["direct_emotional_ending_blocked"] = forbidden
                narrative["choice_ready"] = not forbidden
        elif script_mode == "block_sheet" and block_state is not None:
            if block_ready_for_choice(block_state):
                narrative["choice_ready"] = True
        elif script_mode == "funnel_sheet" and funnel_state is not None:
            if funnel_ready_for_choice(funnel_state):
                narrative["choice_ready"] = True
        elif script_mode == "hybrid_phase_sheet" and hybrid_state is not None:
            selected_order = int(hybrid_selected_row.get("order", 0) or 0)
            if selected_order:
                mark_carona_line_emitted(hybrid_state, selected_order)
            elif hybrid_continuity.startswith("RESPIRO DE CONTINUIDADE"):
                consume_breath(hybrid_state)
            if carona_ready_for_choice(hybrid_state):
                narrative["choice_ready"] = True

        if (
            script_mode not in {"direct_sheet", "hybrid_phase_sheet", "funnel_sheet", "block_sheet"}
            and str(active_chapter.get("choice_ready_when", "") or "").strip()
            and int(narrative.get("chapter_turns", 0) or 0)
            >= int(active_chapter.get("decision_after_turns", 0) or 0)
            and bool(scene.get("microstep_complete", False))
        ):
            # A prontidão fica latched: uma vez surgido o gancho concreto,
            # ele não desaparece se o usuário continuar digitando antes de escolher.
            narrative["choice_ready"] = True

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
            "mary_action": direct_action_text if script_mode == "direct_sheet" else str(scene.get("mary_action", "") or "").strip(),
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

                # Piloto observacional: audita cada turno persistido do roteiro
                # direto. Não injeta lembranças nos prompts e não altera estado.
                if script_mode == "direct_sheet":
                    try:
                        run = str(st.session_state.run_id or "")
                        instance = str(narrative.get("chapter_instance_id", "") or "")
                        branch = str(narrative.get("branch_id", "main") or "main")
                        historical_rows = [
                            {**record, "run_id": run}
                            for record in st.session_state.turn_records
                            if isinstance(record, dict)
                        ]
                        candidates = select_episodic_candidates(
                            historical_rows,
                            run_id=run,
                            chapter_instance_id=instance,
                            branch_id=branch,
                            before_seq=saved_seq,
                            current_user_text=dialogue_text,
                            recent_context=" ".join(
                                str(message.get("content", "") or "")
                                for message in messages_before_turn[-4:]
                                if isinstance(message, dict)
                            ),
                        )
                        save_episodic_memory_audit(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=info["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=run,
                            seq=saved_seq,
                            chapter_id=_chapter_id(),
                            chapter_instance_id=instance,
                            branch_id=branch,
                            line_order=int(direct_row.get("order", 0) or 0),
                            user_text=dialogue_text,
                            candidates=candidates,
                            scene_direction=scene_direction,
                            speaker_explicit=str(
                                (direct_interpretation or {}).get("speaker", "") or ""
                            ),
                            diagnostics=describe_episode_selection(
                                dialogue_text, candidates, before_seq=saved_seq
                            ),
                        )
                    except Exception as episodic_exc:
                        # Auditoria sombra jamais impede a interação principal.
                        _LOG.warning("EPISODIC_MEMORY_AUDIT failed: %s", episodic_exc)
                        st.session_state.audit_error = (
                            "EPISODIC_MEMORY_AUDIT: " + str(episodic_exc)
                        )

                try:
                    save_model_audit(
                        service_account_info=persistence["service_account_info"],
                        spreadsheet_id=info["spreadsheet_id"],
                        spreadsheet_title=persistence["spreadsheet_title"],
                        owner_email=persistence["owner_email"],
                        run_id=st.session_state.run_id,
                        seq=saved_seq,
                        chapter_id=_chapter_id(),
                        user_role=user_role,
                        user_text=dialogue_text,
                        audit=model_audit,
                        branch_id=str(narrative.get("branch_id", "main") or "main"),
                        chapter_instance_id=str(narrative.get("chapter_instance_id", "") or ""),
                        chapter_turn=int(narrative.get("chapter_turns", 0) or 0),
                    )
                except Exception as model_audit_exc:
                    st.session_state.audit_error = str(model_audit_exc)

                if script_mode == "direct_sheet" and direct_state is not None:
                    try:
                        save_direct_script_audit(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=info["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            seq=saved_seq,
                            chapter_id=_chapter_id(),
                            user_text=dialogue_text,
                            mary_text=answer,
                            mary_thought=mary_intent,
                            row=direct_row,
                            state=direct_state,
                            branch_id=str(
                                narrative.get("branch_id", "main") or "main"
                            ),
                            chapter_instance_id=str(
                                narrative.get("chapter_instance_id", "") or ""
                            ),
                            chapter_turn=int(
                                narrative.get("chapter_turns", 0) or 0
                            ),
                        )
                    except Exception as direct_audit_exc:
                        st.session_state.audit_error = str(direct_audit_exc)

                if (
                    script_mode == "block_sheet"
                    and block_row
                    and block_progress
                ):
                    try:
                        save_block_audit(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=info["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            seq=saved_seq,
                            chapter_id=_chapter_id(),
                            user_text=dialogue_text,
                            mary_text=answer,
                            mary_thought=mary_intent,
                            row=block_row,
                            dependency=block_dependency,
                            progress=block_progress,
                            branch_id=str(
                                narrative.get("branch_id", "main")
                                or "main"
                            ),
                            chapter_instance_id=str(
                                narrative.get(
                                    "chapter_instance_id",
                                    "",
                                )
                                or ""
                            ),
                            chapter_turn=int(
                                narrative.get(
                                    "chapter_turns",
                                    0,
                                )
                                or 0
                            ),
                        )
                    except Exception as block_audit_exc:
                        st.session_state.audit_error = str(
                            block_audit_exc
                        )

                if (
                    script_mode == "funnel_sheet"
                    and funnel_row
                    and funnel_progress
                ):
                    try:
                        save_funnel_audit(
                            service_account_info=persistence["service_account_info"],
                            spreadsheet_id=info["spreadsheet_id"],
                            spreadsheet_title=persistence["spreadsheet_title"],
                            owner_email=persistence["owner_email"],
                            run_id=st.session_state.run_id,
                            seq=saved_seq,
                            chapter_id=_chapter_id(),
                            user_text=dialogue_text,
                            mary_text=answer,
                            row=funnel_row,
                            evaluation=funnel_evaluation,
                            progress=funnel_progress,
                            branch_id=str(
                                narrative.get("branch_id", "main")
                                or "main"
                            ),
                            chapter_instance_id=str(
                                narrative.get(
                                    "chapter_instance_id",
                                    "",
                                )
                                or ""
                            ),
                            chapter_turn=int(
                                narrative.get(
                                    "chapter_turns",
                                    0,
                                )
                                or 0
                            ),
                        )
                    except Exception as funnel_audit_exc:
                        st.session_state.audit_error = str(
                            funnel_audit_exc
                        )

                if director_audit and script_mode != "direct_sheet":
                    try:
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
                            branch_id=str(narrative.get("branch_id", "main") or "main"),
                            chapter_instance_id=str(narrative.get("chapter_instance_id", "") or ""),
                            chapter_turn=int(narrative.get("chapter_turns", 0) or 0),
                        )
                        st.session_state.audit_error = ""
                    except Exception as audit_exc:
                        # O turno já foi salvo. Falha de auditoria não torna a história indisponível.
                        st.session_state.audit_error = str(audit_exc)
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
