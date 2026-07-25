from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Any, Callable

import streamlit as st

import repositories.interaction_repository as interaction_repository
import scenarios.service as scenario_service
import ui.paid_chapter_continuation as paid_continuation
import ui.scenario_menu as scenario_menu
from google_sheets_repository import INTERACTIONS_SHEET, obter_registros_aba
from repositories.scenario_session_repository import obter_sessao_cenario


SCENARIO_HISTORY_RECOVERY_VERSION = (
    "scenario-history-recovery-v2-legacy-window-200-turns"
)
_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parse_datetime(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _within_session(record: dict[str, Any], session: dict[str, Any]) -> bool:
    record_time = _parse_datetime(record.get("timestamp"))
    created = _parse_datetime(session.get("created_at"))
    finished = _parse_datetime(
        session.get("completed_at")
        or session.get("last_interaction_at")
        or session.get("updated_at")
    )
    if record_time is None or created is None:
        return False
    if record_time < created:
        return False
    if finished is not None and record_time > finished:
        return False
    return True


def _legacy_records(
    *,
    user_id: str,
    scenario_session_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    session = obter_sessao_cenario(scenario_session_id)
    if not isinstance(session, dict):
        return []
    scenario_id = _text(session.get("scenario_id"))
    if not scenario_id:
        return []

    records = obter_registros_aba(INTERACTIONS_SHEET)
    result: list[dict[str, Any]] = []
    for raw in records:
        if not isinstance(raw, dict):
            continue
        record = dict(raw)
        if _text(record.get("user_id")) != _text(user_id):
            continue
        if _text(record.get("error")):
            continue
        record_session = _text(record.get("scenario_session_id"))
        if record_session and record_session != scenario_session_id:
            continue
        record_scenario = _text(record.get("scenario_id"))
        if record_scenario and record_scenario != scenario_id:
            continue
        if not record_session and not _within_session(record, session):
            continue
        if not _text(record.get("user_text")) and not _text(record.get("mary_response")):
            continue
        result.append(record)

    result.sort(
        key=lambda item: (
            _int(item.get("interaction_number")),
            _text(item.get("timestamp")),
        )
    )
    return result[-max(1, int(limit or 20)):]


def _patch_repository() -> None:
    # O produto já aceita capítulos acima de 50 interações. A chave lógica da
    # persistência precisa acompanhar esse limite para não deixar de agrupar e
    # restaurar turnos após a interação 50.
    interaction_repository.MAX_SCENARIO_INTERACTIONS = 200

    original = interaction_repository.listar_interacoes_sessao_cenario
    if getattr(original, "_mary_history_recovery_wrapped", False):
        return

    @wraps(original)
    def wrapper(
        *,
        user_id: str,
        scenario_session_id: str,
        limite: int = 100,
    ) -> list[dict[str, Any]]:
        result = original(
            user_id=user_id,
            scenario_session_id=scenario_session_id,
            limite=limite,
        )
        if result:
            return result
        return _legacy_records(
            user_id=user_id,
            scenario_session_id=scenario_session_id,
            limit=limite,
        )

    wrapper._mary_history_recovery_wrapped = True  # type: ignore[attr-defined]
    interaction_repository.listar_interacoes_sessao_cenario = wrapper
    scenario_service.listar_interacoes_sessao_cenario = wrapper
    paid_continuation.listar_interacoes_sessao_cenario = wrapper


def aplicar_recuperacao_historico_cenario() -> None:
    _patch_repository()
    scenario_menu.continuar_cenario_para_usuario = (
        scenario_service.continuar_cenario_para_usuario
    )


def install_scenario_history_recovery() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    _ORIGINAL_TITLE = st.title

    @wraps(_ORIGINAL_TITLE)
    def patched_title(*args: Any, **kwargs: Any) -> Any:
        aplicar_recuperacao_historico_cenario()
        assert _ORIGINAL_TITLE is not None
        return _ORIGINAL_TITLE(*args, **kwargs)

    st.title = patched_title
    _INSTALLED = True


__all__ = [
    "SCENARIO_HISTORY_RECOVERY_VERSION",
    "aplicar_recuperacao_historico_cenario",
    "install_scenario_history_recovery",
]
