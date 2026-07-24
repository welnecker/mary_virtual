from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
import hashlib
import os
import sys
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository


SESSION_PERSISTENCE_VERSION = (
    "session-persistence-v1-lifecycle-activity-context"
)

SESSION_COLUMNS = (
    "session_id",
    "user_id",
    "started_at",
    "last_activity_at",
    "ended_at",
    "updated_at",
    "model",
    "prompt_version",
    "app_version",
    "status",
    "end_reason",
    "interaction_count",
    "last_scenario_id",
    "last_scenario_session_id",
    "client_type",
    "runtime_id",
    "duration_seconds",
    "active",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ORIGINAL_CREATE: Callable[..., Any] | None = None
_ORIGINAL_ACTIVITY: Callable[..., Any] | None = None
_ORIGINAL_END: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    text = _texto(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clear_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_sessions() -> list[str]:
    worksheet = sheets_repository.obter_aba(sheets_repository.SESSIONS_SHEET)
    headers = list(
        sheets_repository.obter_cabecalhos(sheets_repository.SESSIONS_SHEET)
    )
    added: list[str] = []
    for column in SESSION_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_caches()
    return added


def _runtime_id() -> str:
    existing = _texto(st.session_state.get("runtime_id"))
    if existing:
        return existing
    seed = f"{os.getpid()}:{datetime.now(timezone.utc).isoformat()}"
    value = "run_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    st.session_state["runtime_id"] = value
    return value


def _client_type() -> str:
    # Streamlit não expõe de forma estável o User-Agent ao script.
    # Mantemos uma classificação segura e extensível.
    return _texto(st.session_state.get("client_type")) or "streamlit_web"


def _scenario_context() -> tuple[str, str]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return "", ""
    return (
        _texto(instance.get("scenario_id")),
        _texto(instance.get("scenario_session_id")),
    )


def _duration_seconds(started_at: Any, ended_at: Any) -> int:
    start = _parse_datetime(started_at)
    end = _parse_datetime(ended_at)
    if start is None or end is None:
        return 0
    return max(0, int((end - start).total_seconds()))


def _patch_repository() -> None:
    global _ORIGINAL_CREATE, _ORIGINAL_ACTIVITY, _ORIGINAL_END

    if _ORIGINAL_CREATE is None:
        _ORIGINAL_CREATE = sheets_repository.criar_sessao
    if _ORIGINAL_ACTIVITY is None:
        _ORIGINAL_ACTIVITY = sheets_repository.atualizar_atividade_sessao
    if _ORIGINAL_END is None:
        _ORIGINAL_END = sheets_repository.encerrar_sessao

    original_create = _ORIGINAL_CREATE
    original_activity = _ORIGINAL_ACTIVITY
    original_end = _ORIGINAL_END

    if not getattr(sheets_repository.criar_sessao, "_robust_session_wrapped", False):
        @wraps(original_create)
        def create_wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            garantir_schema_sessions()
            session = original_create(*args, **kwargs)
            session_id = _texto(session.get("session_id"))
            now = sheets_repository.utc_now_iso()
            changes = {
                "updated_at": now,
                "end_reason": "",
                "interaction_count": 0,
                "last_scenario_id": "",
                "last_scenario_session_id": "",
                "client_type": _client_type(),
                "runtime_id": _runtime_id(),
                "duration_seconds": 0,
                "active": True,
            }
            if session_id:
                sheets_repository.atualizar_registro(
                    sheets_repository.SESSIONS_SHEET,
                    coluna_chave="session_id",
                    valor_chave=session_id,
                    alteracoes=changes,
                )
            session.update(changes)
            st.session_state["technical_session_id"] = session_id
            return session

        create_wrapper._robust_session_wrapped = True  # type: ignore[attr-defined]
        sheets_repository.criar_sessao = create_wrapper

    if not getattr(sheets_repository.atualizar_atividade_sessao, "_robust_session_wrapped", False):
        @wraps(original_activity)
        def activity_wrapper(session_id: str) -> None:
            garantir_schema_sessions()
            original_activity(session_id)
            row = sheets_repository.buscar_registro(
                sheets_repository.SESSIONS_SHEET,
                coluna="session_id",
                valor=session_id,
            ) or {}
            scenario_id, scenario_session_id = _scenario_context()
            now = sheets_repository.utc_now_iso()
            sheets_repository.atualizar_registro(
                sheets_repository.SESSIONS_SHEET,
                coluna_chave="session_id",
                valor_chave=session_id,
                alteracoes={
                    "updated_at": now,
                    "interaction_count": max(
                        0, _inteiro(row.get("interaction_count"), 0)
                    ) + 1,
                    "last_scenario_id": scenario_id,
                    "last_scenario_session_id": scenario_session_id,
                    "status": "active",
                    "active": True,
                },
            )

        activity_wrapper._robust_session_wrapped = True  # type: ignore[attr-defined]
        sheets_repository.atualizar_atividade_sessao = activity_wrapper

    if not getattr(sheets_repository.encerrar_sessao, "_robust_session_wrapped", False):
        @wraps(original_end)
        def end_wrapper(session_id: str, *, reason: str = "normal") -> None:
            garantir_schema_sessions()
            row = sheets_repository.buscar_registro(
                sheets_repository.SESSIONS_SHEET,
                coluna="session_id",
                valor=session_id,
            ) or {}
            original_end(session_id)
            now = sheets_repository.utc_now_iso()
            sheets_repository.atualizar_registro(
                sheets_repository.SESSIONS_SHEET,
                coluna_chave="session_id",
                valor_chave=session_id,
                alteracoes={
                    "updated_at": now,
                    "end_reason": _texto(reason) or "normal",
                    "duration_seconds": _duration_seconds(
                        row.get("started_at"), now
                    ),
                    "status": "ended",
                    "active": False,
                },
            )

        end_wrapper._robust_session_wrapped = True  # type: ignore[attr-defined]
        sheets_repository.encerrar_sessao = end_wrapper


def _patch_app(module: Any) -> None:
    for name in ("criar_sessao", "atualizar_atividade_sessao", "encerrar_sessao"):
        current = getattr(sheets_repository, name, None)
        if callable(current) and hasattr(module, name):
            setattr(module, name, current)


def aplicar_persistencia_sessions() -> None:
    garantir_schema_sessions()
    _patch_repository()
    app_module = sys.modules.get("__main__")
    if app_module is not None:
        _patch_app(app_module)


def install_session_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_sessions()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "SESSION_COLUMNS",
    "SESSION_PERSISTENCE_VERSION",
    "aplicar_persistencia_sessions",
    "garantir_schema_sessions",
    "install_session_persistence",
]
