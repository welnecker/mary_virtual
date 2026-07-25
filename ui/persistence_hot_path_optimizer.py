from __future__ import annotations

from functools import wraps
from typing import Any, Callable

import streamlit as st

import repositories.interaction_repository as interaction_repository
import ui.interaction_persistence as interaction_persistence


PERSISTENCE_HOT_PATH_OPTIMIZER_VERSION = (
    "persistence-hot-path-optimizer-v2-exact-local-count"
)
_INSTALLED = False
_SCHEMA_READY = False
_ORIGINAL_SCHEMA: Callable[..., Any] | None = None
_ORIGINAL_ENRICH: Callable[..., Any] | None = None
_ORIGINAL_COUNT: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _install_schema_cache() -> None:
    global _ORIGINAL_SCHEMA
    current = interaction_persistence.garantir_schema_interactions
    if getattr(current, "_mary_schema_cached", False):
        return
    _ORIGINAL_SCHEMA = current

    @wraps(current)
    def wrapper() -> list[str]:
        global _SCHEMA_READY
        if _SCHEMA_READY:
            return []
        result = current()
        _SCHEMA_READY = True
        return result

    wrapper._mary_schema_cached = True  # type: ignore[attr-defined]
    interaction_persistence.garantir_schema_interactions = wrapper


def _install_success_enrichment_skip() -> None:
    global _ORIGINAL_ENRICH
    current = interaction_persistence._enrich_saved_interaction
    if getattr(current, "_mary_success_enrichment_skipped", False):
        return
    _ORIGINAL_ENRICH = current

    @wraps(current)
    def wrapper(*, kwargs: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> None:
        if not _text(kwargs.get("error")):
            return
        current(kwargs=kwargs, before=before, after=after)

    wrapper._mary_success_enrichment_skipped = True  # type: ignore[attr-defined]
    interaction_persistence._enrich_saved_interaction = wrapper


def _visible_user_message_count() -> int:
    messages = st.session_state.get("messages")
    if not isinstance(messages, list):
        return 0
    return sum(
        1
        for item in messages
        if isinstance(item, dict)
        and _text(item.get("role")) == "user"
        and _text(item.get("content"))
    )


def _current_scenario_count(user_id: str, scenario_session_id: str) -> int:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return 0
    if _text(instance.get("user_id")) not in {"", _text(user_id)}:
        return 0
    if _text(instance.get("scenario_session_id")) != _text(scenario_session_id):
        return 0
    scene = instance.get("scene_state")
    scene_count = _int(scene.get("interaction_count")) if isinstance(scene, dict) else 0
    return max(
        _int(instance.get("interaction_count")),
        scene_count,
        _visible_user_message_count(),
    )


def _install_count_fast_path() -> None:
    global _ORIGINAL_COUNT
    current = interaction_repository.contar_interacoes_sessao_cenario
    if getattr(current, "_mary_count_fast_path", False):
        return
    _ORIGINAL_COUNT = current

    @wraps(current)
    def wrapper(*, user_id: str, scenario_session_id: str) -> int:
        local_count = _current_scenario_count(user_id, scenario_session_id)
        if local_count > 0:
            return local_count
        return current(
            user_id=user_id,
            scenario_session_id=scenario_session_id,
        )

    wrapper._mary_count_fast_path = True  # type: ignore[attr-defined]
    interaction_repository.contar_interacoes_sessao_cenario = wrapper


def install_persistence_hot_path_optimizer() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_schema_cache()
    _install_success_enrichment_skip()
    _install_count_fast_path()
    _INSTALLED = True


__all__ = [
    "PERSISTENCE_HOT_PATH_OPTIMIZER_VERSION",
    "install_persistence_hot_path_optimizer",
]
