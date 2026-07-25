from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
import ui.mary_relationship_persistence as relationship_persistence
from relationship import montar_resumo_estado_relacao, normalizar_estado_relacao


MARY_RELATIONSHIP_COMPACTION_VERSION = (
    "mary-relationship-compaction-v1-safe-cell-limit"
)

# O Google Sheets aceita no máximo 50.000 caracteres por célula. Mantemos uma
# margem ampla para evitar falhas por diferenças de serialização ou caracteres.
_MAX_CELL_CHARS = 40_000
_MAX_STRING_CHARS = 2_000
_MAX_LIST_ITEMS = 20
_MAX_DICT_ITEMS = 80
_MAX_DEPTH = 6

# Somente o núcleo restaurável da relação deve ir para MARY_RELATIONSHIP.
# Dados de prompt, histórico, cena completa e diagnósticos pertencem às abas de
# sessão/interação e não podem crescer dentro de uma única célula.
_ROOT_FIELDS = {
    "state_version",
    "emotional_stage",
    "previous_emotional_stage",
    "sexual_level",
    "previous_sexual_level",
    "trust_level",
    "affection_level",
    "familiarity_level",
    "romantic_tension_level",
    "interaction_count",
    "relationship_summary",
    "sexual_state",
    "mary_internal_state",
    "experience_state",
    "voice_state",
    "current_turn_intent",
    "current_turn_direction",
    "last_turn_intent",
    "last_turn_direction",
    "last_relationship_signals",
    "last_sexual_validation",
    "last_relationship_increments",
    "last_emotional_transition_reason",
    "last_sexual_transition_reason",
    "created_at",
    "updated_at",
}

_DROP_KEYS = {
    "raw_messages",
    "raw_system_prompt",
    "system_prompt",
    "full_prompt",
    "prompt",
    "messages",
    "recent_messages",
    "conversation_history",
    "history",
    "historico",
    "scenario_instance",
    "scene_state",
    "last_director_analysis",
    "director_payload",
    "screenplay",
    "screenplay_text",
    "continuation_context",
}

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _chave_descartavel(key: Any) -> bool:
    normalized = _texto(key).lower()
    if normalized in _DROP_KEYS:
        return True
    return any(
        token in normalized
        for token in (
            "raw_prompt",
            "raw_message",
            "full_prompt",
            "conversation_history",
            "director_payload",
        )
    )


def _compactar_valor(value: Any, *, depth: int = 0) -> Any:
    if depth >= _MAX_DEPTH:
        if isinstance(value, (dict, list, tuple, set)):
            return None

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, str):
        return value[:_MAX_STRING_CHARS]

    if isinstance(value, dict):
        compacted: dict[str, Any] = {}
        for key, item in list(value.items())[:_MAX_DICT_ITEMS]:
            if _chave_descartavel(key):
                continue
            compact_item = _compactar_valor(item, depth=depth + 1)
            if compact_item is not None:
                compacted[str(key)] = compact_item
        return compacted

    if isinstance(value, (list, tuple, set)):
        result: list[Any] = []
        for item in list(value)[:_MAX_LIST_ITEMS]:
            compact_item = _compactar_valor(item, depth=depth + 1)
            if compact_item is not None:
                result.append(compact_item)
        return result

    return _texto(value)[:_MAX_STRING_CHARS]


def compactar_estado_relacao_para_persistencia(
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = normalizar_estado_relacao(state)
    selected = {
        key: deepcopy(normalized.get(key))
        for key in _ROOT_FIELDS
        if key in normalized
    }
    compacted = _compactar_valor(selected)
    return compacted if isinstance(compacted, dict) else {}


def _serializar_estado_com_limite(state: dict[str, Any]) -> str:
    serialized = sheets_repository.serializar_json(state)
    if len(serialized) <= _MAX_CELL_CHARS:
        return serialized

    # Primeiro descarte campos transitórios que podem ser reconstruídos no turno.
    reduced = dict(state)
    for field in (
        "current_turn_intent",
        "current_turn_direction",
        "last_turn_intent",
        "last_turn_direction",
        "last_relationship_signals",
        "last_sexual_validation",
        "last_relationship_increments",
    ):
        reduced.pop(field, None)

    serialized = sheets_repository.serializar_json(reduced)
    if len(serialized) <= _MAX_CELL_CHARS:
        return serialized

    # Último fallback: persiste apenas o núcleo estável. Isso preserva vínculo,
    # progressão e estado sexual sem arriscar derrubar a gravação da interação.
    stable_fields = {
        "state_version",
        "emotional_stage",
        "previous_emotional_stage",
        "sexual_level",
        "previous_sexual_level",
        "trust_level",
        "affection_level",
        "familiarity_level",
        "romantic_tension_level",
        "interaction_count",
        "relationship_summary",
        "sexual_state",
        "mary_internal_state",
        "experience_state",
        "voice_state",
        "created_at",
        "updated_at",
    }
    minimal = {
        key: value
        for key, value in reduced.items()
        if key in stable_fields
    }
    serialized = sheets_repository.serializar_json(minimal)
    return serialized[:_MAX_CELL_CHARS]


def sincronizar_estado_relacionamento_compacto(
    interaction_record: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    user = (
        st.session_state.get("persistent_user")
        or st.session_state.get("auth_user")
        or {}
    )
    if not isinstance(user, dict):
        return None

    user_id = _texto(user.get("user_id"))
    if not user_id:
        return None

    full_state = normalizar_estado_relacao(
        st.session_state.get("relationship_state")
    )
    compact_state = compactar_estado_relacao_para_persistencia(full_state)

    scenario = st.session_state.get("scenario_instance")
    scenario = scenario if isinstance(scenario, dict) else {}
    interaction_record = (
        interaction_record if isinstance(interaction_record, dict) else {}
    )

    try:
        summary_data = montar_resumo_estado_relacao(full_state)
        summary = sheets_repository.serializar_json(summary_data)
    except Exception:
        summary = ""

    payload = {
        "relationship_summary": summary[:_MAX_CELL_CHARS],
        "relationship_state_json": _serializar_estado_com_limite(compact_state),
        "last_interaction_at": (
            _texto(interaction_record.get("timestamp"))
            or sheets_repository.utc_now_iso()
        ),
        "last_scenario_id": _texto(scenario.get("scenario_id")),
        "last_scenario_session_id": _texto(
            scenario.get("scenario_session_id")
        ),
        "status": "active",
        "active": True,
    }

    updated = relationship_persistence.atualizar_relacionamento_mary(
        user_id,
        payload,
    )
    st.session_state["mary_relationship"] = updated
    return updated


def aplicar_compactacao_relacionamento_mary() -> None:
    relationship_persistence.sincronizar_estado_relacionamento = (
        sincronizar_estado_relacionamento_compacto
    )


def install_mary_relationship_compaction() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return

    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_compactacao_relacionamento_mary()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "MARY_RELATIONSHIP_COMPACTION_VERSION",
    "aplicar_compactacao_relacionamento_mary",
    "compactar_estado_relacao_para_persistencia",
    "install_mary_relationship_compaction",
    "sincronizar_estado_relacionamento_compacto",
]
