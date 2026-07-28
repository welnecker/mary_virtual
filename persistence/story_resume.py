from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

from core.story_models import StorySession
from google_sheets_repository import obter_registros_aba
from .interaction_history import interaction_rows_for_session

SCENARIO_SESSIONS_SHEET = "SCENARIO_SESSIONS"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value if value not in (None, "") else default))
    except (TypeError, ValueError):
        return default


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = _text(value).lower()
    if text in {"true", "1", "sim", "yes", "active", "ativo"}:
        return True
    if text in {"false", "0", "nao", "não", "no", "inactive", "inativo"}:
        return False
    return default


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    text = _text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_active_row(row: dict[str, Any]) -> bool:
    status = (_text(row.get("status")) or "active").lower()
    active = _bool(row.get("active"), status == "active")
    input_locked = _bool(row.get("input_locked"), False)
    ending_sent = _bool(row.get("ending_sent"), False)
    return status == "active" and active and not input_locked and not ending_sent


def _enrich_with_interactions(row: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    result = dict(row)
    session_id = _text(result.get("scenario_session_id"))
    interactions = interaction_rows_for_session(
        scenario_session_id=session_id,
        user_id=user_id,
    )
    result["saved_interaction_count"] = len(interactions)
    if interactions:
        latest = interactions[-1]
        result["last_user_text"] = _text(latest.get("user_text"))
        result["last_mary_response"] = _text(latest.get("mary_response"))
        result["last_interaction_number"] = _int(latest.get("interaction_number"), len(interactions))
        result["last_interaction_timestamp"] = _text(
            latest.get("timestamp") or latest.get("updated_at")
        )
    else:
        result["last_user_text"] = ""
        result["last_mary_response"] = ""
        result["last_interaction_number"] = 0
        result["last_interaction_timestamp"] = ""
    return result


def _time_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _text(row.get("last_interaction_timestamp") or row.get("last_interaction_at") or row.get("updated_at")),
        _text(row.get("created_at")),
        _text(row.get("scenario_session_id")),
    )


def _legacy_supermarket_session(row: dict[str, Any]) -> bool:
    return (
        _text(row.get("scenario_id")) == "casada_frustrada"
        and _text(row.get("current_phase")) == "chapter_01"
        and not _is_active_row(row)
        and _int(row.get("saved_interaction_count"), 0) > 0
    )


def _choose_story_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active_with_history = [
        row for row in rows
        if _is_active_row(row) and _int(row.get("saved_interaction_count"), 0) > 0
    ]
    if active_with_history:
        return max(active_with_history, key=_time_key)

    legacy_history = [row for row in rows if _legacy_supermarket_session(row)]
    if legacy_history:
        legacy = dict(max(legacy_history, key=_time_key))
        legacy["resume_legacy_supermarket"] = True
        return legacy

    active_empty = [row for row in rows if _is_active_row(row)]
    if active_empty:
        return max(active_empty, key=_time_key)

    with_history = [row for row in rows if _int(row.get("saved_interaction_count"), 0) > 0]
    if with_history:
        return max(with_history, key=_time_key)
    return max(rows, key=_time_key)


def latest_story_sessions_by_scenario(*, user_id: str) -> dict[str, dict[str, Any]]:
    """Retorna a melhor execução retomável de cada história."""
    user_id = _text(user_id)
    if not user_id:
        return {}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in obter_registros_aba(SCENARIO_SESSIONS_SHEET):
        row = dict(raw)
        if _text(row.get("user_id")) != user_id:
            continue
        scenario_id = _text(row.get("scenario_id"))
        if not scenario_id:
            continue
        grouped.setdefault(scenario_id, []).append(
            _enrich_with_interactions(row, user_id=user_id)
        )

    return {
        scenario_id: _choose_story_row(rows)
        for scenario_id, rows in grouped.items()
        if rows
    }


def catalog_story_state(row: dict[str, Any] | None) -> str:
    if not isinstance(row, dict):
        return "new"
    if _int(row.get("saved_interaction_count"), 0) > 0:
        return "active"
    return "active" if _is_active_row(row) else "finished"


def _migrate_legacy_payload(row: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not _bool(row.get("resume_legacy_supermarket"), False):
        return payload

    migrated = dict(payload)
    migrated.update(
        {
            "chapter_id": "full_story",
            "current_beat": "home_first_message",
            "status": "active",
            "current_beat_emitted": False,
            "turn_count": max(
                _int(row.get("saved_interaction_count"), 0),
                _int(payload.get("turn_count"), 0),
            ),
            "ending_reason": "",
            "alignment_warning_active": False,
            "alignment_warning_reason": "",
        }
    )
    migrated["completed_beats"] = [
        "injury_check",
        "recognize_plaza",
        "first_farewell",
        "second_encounter",
        "market_crowded",
        "cart_single_guess",
        "home_weekend_routine",
        "checkout_turn",
        "ask_wait_help_car",
        "open_trunk",
        "liked_meeting",
        "request_phone",
        "exchange_numbers",
        "car_farewell",
    ]
    migrated["completed_facts"] = [
        "first_contact_closed",
        "second_encounter_started",
        "single_status_explored",
        "help_to_car_completed",
        "phone_numbers_exchanged",
    ]
    return migrated


def hydrate_story_session(row: dict[str, Any]) -> StorySession:
    """Reconstrói a sessão e migra o encerramento legado do supermercado."""
    if not isinstance(row, dict):
        raise ValueError("Registro de sessão narrativa inválido.")

    progress = _json_dict(row.get("story_progress_json"))
    engine_data = progress.get("engine")
    engine_data = dict(engine_data) if isinstance(engine_data, dict) else {}

    allowed = {field.name for field in fields(StorySession)}
    payload = {key: value for key, value in engine_data.items() if key in allowed}
    payload.update(
        {
            "access_id": _text(
                payload.get("access_id")
                or progress.get("access_id")
                or row.get("scenario_session_id")
            ),
            "story_id": _text(payload.get("story_id") or row.get("scenario_id")),
            "chapter_id": _text(
                payload.get("chapter_id")
                or progress.get("chapter_id")
                or row.get("current_phase")
            ),
            "current_beat": _text(payload.get("current_beat") or row.get("current_beat")),
            "status": _text(payload.get("status") or row.get("status") or "active"),
            "turn_count": _int(payload.get("turn_count"), _int(row.get("interaction_count"), 0)),
            "ending_reason": _text(payload.get("ending_reason") or row.get("ending_reason")),
        }
    )

    payload.setdefault("completed_beats", list(progress.get("completed_beats") or []))
    payload.setdefault("completed_facts", list(progress.get("completed_facts") or []))
    payload.setdefault("current_beat_emitted", False)
    payload.setdefault("alignment_warning_active", False)
    payload.setdefault("alignment_warning_reason", "")
    payload = _migrate_legacy_payload(row, payload)

    if not payload["access_id"] or not payload["story_id"]:
        raise ValueError("A sessão persistida não possui identificadores obrigatórios.")
    if not payload["chapter_id"] or not payload["current_beat"]:
        raise ValueError("A sessão persistida não possui capítulo ou beat atual.")
    return StorySession(**payload)


__all__ = [
    "catalog_story_state",
    "hydrate_story_session",
    "latest_story_sessions_by_scenario",
]
