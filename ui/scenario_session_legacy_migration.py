from __future__ import annotations

import hashlib
import json
from functools import wraps
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository


SCENARIO_SESSION_MIGRATION_VERSION = (
    "scenario-session-migration-v2-canonical-continuity-metadata"
)
LEGACY_SCENARIO_SESSIONS_SHEET = "USER_SCENARIO_SESSIONS"
CANONICAL_SCENARIO_SESSIONS_SHEET = "SCENARIO_SESSIONS"

CANONICAL_SCENARIO_SESSION_COLUMNS = (
    "scenario_session_id",
    "user_id",
    "scenario_id",
    "scenario_version",
    "created_at",
    "updated_at",
    "last_interaction_at",
    "completed_at",
    "status",
    "interaction_count",
    "opening_sent",
    "current_phase",
    "current_route",
    "current_beat",
    "active_hook",
    "climax_reached",
    "satisfaction_detected",
    "ending_ready",
    "ending_sent",
    "ending_type",
    "ending_reason",
    "input_locked",
    "show_return_to_menu",
    "scene_state_json",
    "story_progress_json",
    "summary",
    "relationship_state_json",
    "chapter_number",
    "parent_session_id",
    "root_session_id",
    "continuation_mode",
    "history_session_ids_json",
    "save_revision",
    "state_checksum",
    "active",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None
_MIGRATION_ATTEMPTED = False


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _booleano(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = _texto(value).lower()
    if text in {"true", "1", "sim", "yes", "verdadeiro", "active", "ativo"}:
        return True
    if text in {"false", "0", "nao", "não", "no", "falso", "inactive", "inativo", ""}:
        return False
    return default


def _inteiro(value: Any, *, default: int = 0) -> int:
    try:
        return int(float(value if value not in (None, "") else default))
    except (TypeError, ValueError):
        return default


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _texto(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    text = _texto(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _normalizar_ids(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in _json_list(value) if not isinstance(value, list) else value:
        text = _texto(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _checksum(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _clear_sheet_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_scenario_sessions() -> list[str]:
    worksheet = sheets_repository.obter_aba(
        CANONICAL_SCENARIO_SESSIONS_SHEET
    )
    headers = list(
        sheets_repository.obter_cabecalhos(
            CANONICAL_SCENARIO_SESSIONS_SHEET
        )
    )
    added: list[str] = []
    for column in CANONICAL_SCENARIO_SESSION_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_sheet_caches()
    return added


def _normalizar_registro_legado(record: dict[str, Any]) -> dict[str, Any]:
    now = sheets_repository.utc_now_iso()
    story_progress = _json_dict(record.get("story_progress_json"))
    session_id = _texto(record.get("scenario_session_id"))
    status = _texto(record.get("status")) or "active"
    ending_sent = _booleano(record.get("ending_sent"))
    completed = status.lower() == "completed" or ending_sent
    completed_at = _texto(record.get("completed_at"))
    if completed and not completed_at:
        completed_at = _texto(record.get("updated_at")) or now

    chapter_number = max(
        1,
        _inteiro(
            record.get("chapter_number") or story_progress.get("chapter_number"),
            default=1,
        ),
    )
    parent_session_id = _texto(
        record.get("parent_session_id") or story_progress.get("parent_session_id")
    )
    root_session_id = _texto(
        record.get("root_session_id") or story_progress.get("root_session_id")
    ) or parent_session_id or session_id
    continuation_mode = _texto(
        record.get("continuation_mode") or story_progress.get("continuation_mode")
    )
    history_ids = _normalizar_ids(
        record.get("history_session_ids_json")
        or story_progress.get("history_session_ids")
        or []
    )
    if parent_session_id and parent_session_id not in history_ids:
        history_ids.append(parent_session_id)

    scene_json = _texto(record.get("scene_state_json")) or "{}"
    story_json = _texto(record.get("story_progress_json")) or "{}"
    relationship_json = _texto(record.get("relationship_state_json")) or "{}"

    return {
        "scenario_session_id": session_id,
        "user_id": _texto(record.get("user_id")),
        "scenario_id": _texto(record.get("scenario_id")),
        "scenario_version": max(
            1, _inteiro(record.get("scenario_version"), default=1)
        ),
        "created_at": _texto(record.get("created_at")) or now,
        "updated_at": _texto(record.get("updated_at")) or now,
        "last_interaction_at": _texto(record.get("last_interaction_at")),
        "completed_at": completed_at,
        "status": "completed" if completed else status,
        "interaction_count": max(
            0, _inteiro(record.get("interaction_count"), default=0)
        ),
        "opening_sent": _booleano(record.get("opening_sent")),
        "current_phase": _texto(record.get("current_phase")),
        "current_route": _texto(record.get("current_route")),
        "current_beat": _texto(record.get("current_beat")),
        "active_hook": _texto(record.get("active_hook")),
        "climax_reached": _booleano(record.get("climax_reached")),
        "satisfaction_detected": _booleano(record.get("satisfaction_detected")),
        "ending_ready": _booleano(record.get("ending_ready")),
        "ending_sent": ending_sent,
        "ending_type": _texto(record.get("ending_type")),
        "ending_reason": _texto(record.get("ending_reason")),
        "input_locked": _booleano(record.get("input_locked")),
        "show_return_to_menu": _booleano(record.get("show_return_to_menu")),
        "scene_state_json": scene_json,
        "story_progress_json": story_json,
        "summary": _texto(record.get("summary")),
        "relationship_state_json": relationship_json,
        "chapter_number": chapter_number,
        "parent_session_id": parent_session_id,
        "root_session_id": root_session_id,
        "continuation_mode": continuation_mode,
        "history_session_ids_json": sheets_repository.serializar_json(history_ids),
        "save_revision": max(1, _inteiro(record.get("save_revision"), default=1)),
        "state_checksum": _texto(record.get("state_checksum")) or _checksum(
            scene_json, story_json, relationship_json
        ),
        "active": not completed and status.lower() == "active",
    }


def migrar_user_scenario_sessions() -> dict[str, int]:
    """Copia registros legados ausentes; nunca sobrescreve a aba oficial."""
    garantir_schema_scenario_sessions()

    try:
        legacy_records = sheets_repository.obter_registros_aba(
            LEGACY_SCENARIO_SESSIONS_SHEET
        )
    except Exception:
        return {"found": 0, "migrated": 0, "skipped": 0, "invalid": 0}

    canonical_records = sheets_repository.obter_registros_aba(
        CANONICAL_SCENARIO_SESSIONS_SHEET
    )
    canonical_ids = {
        _texto(record.get("scenario_session_id"))
        for record in canonical_records
        if _texto(record.get("scenario_session_id"))
    }

    migrated = 0
    skipped = 0
    invalid = 0
    for legacy in legacy_records:
        if not isinstance(legacy, dict):
            invalid += 1
            continue
        record = _normalizar_registro_legado(legacy)
        session_id = record["scenario_session_id"]
        if not session_id or not record["user_id"] or not record["scenario_id"]:
            invalid += 1
            continue
        if session_id in canonical_ids:
            skipped += 1
            continue
        sheets_repository.adicionar_registro(
            CANONICAL_SCENARIO_SESSIONS_SHEET,
            record,
        )
        canonical_ids.add(session_id)
        migrated += 1

    return {
        "found": len(legacy_records),
        "migrated": migrated,
        "skipped": skipped,
        "invalid": invalid,
    }


def aplicar_migracao_sessoes_legadas() -> None:
    global _MIGRATION_ATTEMPTED
    if _MIGRATION_ATTEMPTED:
        return
    _MIGRATION_ATTEMPTED = True
    try:
        result = migrar_user_scenario_sessions()
    except Exception as exc:
        st.warning(
            "Não foi possível verificar a aba legada de sessões narrativas: "
            f"{exc}"
        )
        return

    if result.get("migrated", 0):
        st.info(
            "Sessões narrativas legadas migradas para SCENARIO_SESSIONS: "
            f"{result['migrated']}."
        )


def install_scenario_session_legacy_migration() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_migracao_sessoes_legadas()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "CANONICAL_SCENARIO_SESSION_COLUMNS",
    "SCENARIO_SESSION_MIGRATION_VERSION",
    "aplicar_migracao_sessoes_legadas",
    "garantir_schema_scenario_sessions",
    "install_scenario_session_legacy_migration",
    "migrar_user_scenario_sessions",
]
