from __future__ import annotations

from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository
import repositories.interaction_repository as interaction_repository


INTERACTION_PERSISTENCE_VERSION = (
    "interaction-persistence-v1-narrative-fields-error-trace"
)

INTERACTION_COLUMNS = (
    "interaction_id",
    "session_id",
    "user_id",
    "timestamp",
    "updated_at",
    "user_text",
    "mary_response",
    "model",
    "prompt_version",
    "app_version",
    "response_time_ms",
    "image_sent",
    "image_width",
    "image_height",
    "image_size_bytes",
    "image_mime_type",
    "mary_asked_name",
    "error",
    "error_type",
    "error_stage",
    "retry_count",
    "scenario_session_id",
    "scenario_id",
    "scenario_version",
    "scenario_phase",
    "scenario_route",
    "scenario_beat",
    "scenario_status",
    "interaction_number",
    "scenario_completed",
    "interaction_key",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_ORIGINAL_SAVE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _booleano(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return _texto(value).lower() in {
        "true", "1", "sim", "yes", "verdadeiro"
    }


def _clear_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_interactions() -> list[str]:
    worksheet = sheets_repository.obter_aba(
        sheets_repository.INTERACTIONS_SHEET
    )
    headers = list(
        sheets_repository.obter_cabecalhos(
            sheets_repository.INTERACTIONS_SHEET
        )
    )
    added: list[str] = []
    for column in INTERACTION_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_caches()
    return added


def _interaction_key(
    *, scenario_session_id: str, interaction_number: int
) -> str:
    session_id = _texto(scenario_session_id)
    number = _inteiro(interaction_number, 0)
    if not session_id or number < 1:
        return ""
    return f"{session_id}:{number:03d}"


def _classificar_erro(error: str) -> tuple[str, str]:
    text = _texto(error)
    if not text:
        return "", ""
    lowered = text.lower()
    if any(token in lowered for token in ("timeout", "timed out")):
        return "timeout", "model_call"
    if any(token in lowered for token in ("429", "rate limit", "quota")):
        return "rate_limit", "model_call"
    if any(token in lowered for token in ("connection", "connecting", "network")):
        return "connection", "transport"
    if any(token in lowered for token in ("google sheets", "gspread", "apierror")):
        return "persistence", "google_sheets"
    if any(token in lowered for token in ("json", "parse", "decode")):
        return "parse", "response_processing"
    return "runtime", "unknown"


def _scenario_snapshot() -> dict[str, Any]:
    instance = st.session_state.get("scenario_instance")
    if not isinstance(instance, dict):
        return {}
    return {
        "scenario_session_id": _texto(instance.get("scenario_session_id")),
        "scenario_id": _texto(instance.get("scenario_id")),
        "scenario_version": max(1, _inteiro(instance.get("scenario_version"), 1)),
        "scenario_phase": _texto(instance.get("current_phase")),
        "scenario_route": _texto(instance.get("current_route")),
        "scenario_beat": _texto(instance.get("current_beat")),
        "scenario_status": _texto(instance.get("status")) or "active",
        "interaction_number": max(0, _inteiro(instance.get("interaction_count"), 0)),
        "scenario_completed": (
            _texto(instance.get("status")).lower() == "completed"
            or _booleano(instance.get("ending_sent"), False)
        ),
    }


def _patch_key_builder() -> None:
    interaction_repository.MAX_SCENARIO_INTERACTIONS = 9999
    interaction_repository.montar_interaction_key = _interaction_key


def _enrich_saved_interaction(
    *, kwargs: dict[str, Any], before: dict[str, Any], after: dict[str, Any]
) -> None:
    interaction_id = _texto(kwargs.get("interaction_id"))
    error = _texto(kwargs.get("error"))
    error_type, error_stage = _classificar_erro(error)
    snapshot = after or before

    interaction_number = _inteiro(kwargs.get("interaction_number"), 0)
    if interaction_number < 1:
        interaction_number = _inteiro(snapshot.get("interaction_number"), 0)
    scenario_session_id = _texto(snapshot.get("scenario_session_id"))
    interaction_key = _interaction_key(
        scenario_session_id=scenario_session_id,
        interaction_number=interaction_number,
    )

    changes = {
        "updated_at": sheets_repository.utc_now_iso(),
        "app_version": _texto(st.session_state.get("app_version")),
        "error_type": error_type,
        "error_stage": error_stage,
        "retry_count": max(0, _inteiro(kwargs.get("retry_count"), 0)),
        "scenario_session_id": scenario_session_id,
        "scenario_id": _texto(snapshot.get("scenario_id")),
        "scenario_version": snapshot.get("scenario_version", ""),
        "scenario_phase": _texto(snapshot.get("scenario_phase")),
        "scenario_route": _texto(snapshot.get("scenario_route")),
        "scenario_beat": _texto(snapshot.get("scenario_beat")),
        "scenario_status": _texto(snapshot.get("scenario_status")),
        "interaction_number": interaction_number if interaction_key else "",
        "scenario_completed": bool(snapshot.get("scenario_completed", False)),
        "interaction_key": interaction_key,
    }

    if interaction_key and not error:
        updated = sheets_repository.atualizar_registro(
            sheets_repository.INTERACTIONS_SHEET,
            coluna_chave="interaction_key",
            valor_chave=interaction_key,
            alteracoes=changes,
        )
        if updated:
            return
    if interaction_id:
        sheets_repository.atualizar_registro(
            sheets_repository.INTERACTIONS_SHEET,
            coluna_chave="interaction_id",
            valor_chave=interaction_id,
            alteracoes=changes,
        )


def _patch_save(module: Any) -> None:
    global _ORIGINAL_SAVE
    original = getattr(module, "salvar_interacao", None)
    if not callable(original) or getattr(original, "_robust_interaction_wrapped", False):
        return
    if _ORIGINAL_SAVE is None:
        _ORIGINAL_SAVE = original

    @wraps(original)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        garantir_schema_interactions()
        before = _scenario_snapshot()
        result = original(*args, **kwargs)
        after = _scenario_snapshot()
        try:
            _enrich_saved_interaction(
                kwargs=dict(kwargs), before=before, after=after
            )
        except sheets_repository.GoogleSheetsRepositoryError as exc:
            st.warning(
                "A interação foi salva, mas seus metadados técnicos não "
                f"puderam ser completados: {exc}"
            )
        return result

    wrapper._robust_interaction_wrapped = True  # type: ignore[attr-defined]
    module.salvar_interacao = wrapper


def aplicar_persistencia_interactions() -> None:
    garantir_schema_interactions()
    _patch_key_builder()
    _patch_save(interaction_repository)
    app_module = sys.modules.get("__main__")
    if app_module is not None:
        _patch_save(app_module)


def install_interaction_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_interactions()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "INTERACTION_COLUMNS",
    "INTERACTION_PERSISTENCE_VERSION",
    "aplicar_persistencia_interactions",
    "garantir_schema_interactions",
    "install_interaction_persistence",
]
