from __future__ import annotations

from copy import deepcopy
from functools import wraps
import sys
from typing import Any, Callable

import streamlit as st

import google_sheets_repository as sheets_repository


SCENARIO_EVENT_PERSISTENCE_VERSION = (
    "scenario-event-persistence-v1-audit-trail-deduplicated"
)
SCENARIO_EVENTS_SHEET = "SCENARIO_EVENTS"

SCENARIO_EVENT_COLUMNS = (
    "event_id",
    "event_key",
    "scenario_session_id",
    "user_id",
    "scenario_id",
    "scenario_version",
    "interaction_number",
    "created_at",
    "updated_at",
    "event_type",
    "previous_phase",
    "new_phase",
    "previous_route",
    "new_route",
    "previous_beat",
    "new_beat",
    "previous_hook",
    "new_hook",
    "previous_status",
    "new_status",
    "user_action",
    "director_decision",
    "active_hook",
    "event_data_json",
)

_INSTALLED = False
_ORIGINAL_TITLE: Callable[..., Any] | None = None


def _texto(value: Any) -> str:
    return str(value or "").strip()


def _inteiro(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _clear_sheet_caches() -> None:
    for name in ("obter_cabecalhos", "obter_registros_aba"):
        function = getattr(sheets_repository, name, None)
        clear = getattr(function, "clear", None)
        if callable(clear):
            clear()


def garantir_schema_scenario_events() -> list[str]:
    worksheet = sheets_repository.obter_aba(SCENARIO_EVENTS_SHEET)
    headers = list(sheets_repository.obter_cabecalhos(SCENARIO_EVENTS_SHEET))
    added: list[str] = []
    for column in SCENARIO_EVENT_COLUMNS:
        if column in headers:
            continue
        headers.append(column)
        worksheet.update_cell(1, len(headers), column)
        added.append(column)
    if added:
        _clear_sheet_caches()
    return added


def _snapshot(instance: Any) -> dict[str, Any]:
    if not isinstance(instance, dict):
        return {}
    scene_state = instance.get("scene_state")
    scene_state = deepcopy(scene_state) if isinstance(scene_state, dict) else {}
    return {
        "scenario_session_id": _texto(instance.get("scenario_session_id")),
        "user_id": _texto(instance.get("user_id")),
        "scenario_id": _texto(instance.get("scenario_id")),
        "scenario_version": _inteiro(instance.get("scenario_version"), 1),
        "interaction_number": _inteiro(instance.get("interaction_count"), 0),
        "phase": _texto(instance.get("current_phase")),
        "route": _texto(instance.get("current_route")),
        "beat": _texto(instance.get("current_beat")),
        "hook": _texto(instance.get("active_hook")),
        "status": _texto(instance.get("status")) or "active",
        "scene_state": scene_state,
    }


def _director_decision(snapshot: dict[str, Any]) -> str:
    scene_state = snapshot.get("scene_state")
    if not isinstance(scene_state, dict):
        return ""
    for key in (
        "director_decision",
        "last_director_decision",
        "narrative_direction",
        "last_direction",
        "decision",
    ):
        value = scene_state.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict) and value:
            return sheets_repository.serializar_json(value)
    return ""


def _event_type(previous: dict[str, Any], current: dict[str, Any]) -> str:
    changes: list[str] = []
    if previous.get("phase") != current.get("phase"):
        changes.append("phase")
    if previous.get("route") != current.get("route"):
        changes.append("route")
    if previous.get("beat") != current.get("beat"):
        changes.append("beat")
    if previous.get("hook") != current.get("hook"):
        changes.append("hook")
    if previous.get("status") != current.get("status"):
        changes.append("status")
    return "transition:" + "+".join(changes) if changes else "director_turn"


def registrar_evento_cenario(
    record: dict[str, Any] | None,
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any] | None:
    session_id = _texto(current.get("scenario_session_id"))
    user_id = _texto(current.get("user_id"))
    scenario_id = _texto(current.get("scenario_id"))
    interaction_number = _inteiro(current.get("interaction_number"), 0)
    if not session_id or not user_id or not scenario_id or interaction_number < 1:
        return None

    garantir_schema_scenario_events()
    event_type = _event_type(previous, current)
    event_key = f"{session_id}:{interaction_number:03d}:{event_type}"
    now = sheets_repository.utc_now_iso()
    record = record if isinstance(record, dict) else {}
    payload = {
        "event_id": "evt_" + event_key.replace(":", "_"),
        "event_key": event_key,
        "scenario_session_id": session_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "scenario_version": _inteiro(current.get("scenario_version"), 1),
        "interaction_number": interaction_number,
        "created_at": now,
        "updated_at": now,
        "event_type": event_type,
        "previous_phase": _texto(previous.get("phase")),
        "new_phase": _texto(current.get("phase")),
        "previous_route": _texto(previous.get("route")),
        "new_route": _texto(current.get("route")),
        "previous_beat": _texto(previous.get("beat")),
        "new_beat": _texto(current.get("beat")),
        "previous_hook": _texto(previous.get("hook")),
        "new_hook": _texto(current.get("hook")),
        "previous_status": _texto(previous.get("status")),
        "new_status": _texto(current.get("status")),
        "user_action": _texto(record.get("user_text")),
        "director_decision": _director_decision(current),
        "active_hook": _texto(current.get("hook")),
        "event_data_json": sheets_repository.serializar_json(
            {
                "previous": previous,
                "current": current,
                "interaction_id": _texto(record.get("interaction_id")),
                "mary_response": _texto(record.get("mary_response")),
            }
        ),
    }

    existing = sheets_repository.buscar_registro(
        SCENARIO_EVENTS_SHEET,
        coluna="event_key",
        valor=event_key,
    )
    if existing is None:
        sheets_repository.adicionar_registro(SCENARIO_EVENTS_SHEET, payload)
    else:
        changes = dict(payload)
        changes.pop("event_id", None)
        changes.pop("event_key", None)
        changes.pop("created_at", None)
        sheets_repository.atualizar_registro(
            SCENARIO_EVENTS_SHEET,
            coluna_chave="event_key",
            valor_chave=event_key,
            alteracoes=changes,
        )
    return payload


def _patch_app(module: Any) -> None:
    original = getattr(module, "registrar_interacao_local_e_remota", None)
    if not callable(original) or getattr(original, "_scenario_events_wrapped", False):
        return

    @wraps(original)
    def wrapper(record: dict[str, Any]) -> Any:
        current_before = _snapshot(st.session_state.get("scenario_instance"))
        result = original(record)
        current = _snapshot(st.session_state.get("scenario_instance"))
        session_id = _texto(current.get("scenario_session_id"))
        snapshots = st.session_state.setdefault("scenario_event_snapshots", {})
        previous = snapshots.get(session_id) if isinstance(snapshots, dict) else None
        previous = previous if isinstance(previous, dict) else current_before

        if isinstance(record, dict) and not _texto(record.get("error")):
            try:
                registrar_evento_cenario(record, previous, current)
            except sheets_repository.GoogleSheetsRepositoryError as exc:
                st.warning(
                    "A interação foi salva, mas o evento narrativo não pôde "
                    f"ser registrado: {exc}"
                )

        if isinstance(snapshots, dict) and session_id:
            snapshots[session_id] = current
            st.session_state["scenario_event_snapshots"] = snapshots
        return result

    wrapper._scenario_events_wrapped = True  # type: ignore[attr-defined]
    module.registrar_interacao_local_e_remota = wrapper


def aplicar_persistencia_scenario_events() -> None:
    garantir_schema_scenario_events()
    app_module = sys.modules.get("__main__")
    if app_module is not None:
        _patch_app(app_module)


def install_scenario_event_persistence() -> None:
    global _INSTALLED, _ORIGINAL_TITLE
    if _INSTALLED:
        return
    original_title = st.title
    _ORIGINAL_TITLE = original_title

    @wraps(original_title)
    def title_wrapper(*args: Any, **kwargs: Any) -> Any:
        aplicar_persistencia_scenario_events()
        return original_title(*args, **kwargs)

    st.title = title_wrapper
    _INSTALLED = True


__all__ = [
    "SCENARIO_EVENT_COLUMNS",
    "SCENARIO_EVENT_PERSISTENCE_VERSION",
    "aplicar_persistencia_scenario_events",
    "garantir_schema_scenario_events",
    "install_scenario_event_persistence",
    "registrar_evento_cenario",
]
