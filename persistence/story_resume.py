from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

from core.story_models import StorySession
from google_sheets_repository import obter_registros_aba

SCENARIO_SESSIONS_SHEET = "SCENARIO_SESSIONS"
INTERACTIONS_SHEET = "INTERACTIONS"


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


def _sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _text(row.get("last_interaction_at") or row.get("updated_at")),
        _text(row.get("created_at")),
        _text(row.get("scenario_session_id")),
    )


def _interaction_sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (
        _int(row.get("interaction_number"), 0),
        _text(row.get("timestamp") or row.get("updated_at")),
        _text(row.get("interaction_id")),
    )


def latest_story_sessions_by_scenario(*, user_id: str) -> dict[str, dict[str, Any]]:
    """Retorna a execução mais recente de cada história, com a última interação salva."""
    user_id = _text(user_id)
    if not user_id:
        return {}

    rows = [
        dict(row)
        for row in obter_registros_aba(SCENARIO_SESSIONS_SHEET)
        if _text(row.get("user_id")) == user_id
        and _text(row.get("scenario_id"))
    ]
    rows.sort(key=_sort_key, reverse=True)

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        scenario_id = _text(row.get("scenario_id"))
        result.setdefault(scenario_id, row)

    session_ids = {
        _text(row.get("scenario_session_id"))
        for row in result.values()
        if _text(row.get("scenario_session_id"))
    }
    if not session_ids:
        return result

    latest_by_session: dict[str, dict[str, Any]] = {}
    for raw in obter_registros_aba(INTERACTIONS_SHEET):
        row = dict(raw)
        session_id = _text(row.get("scenario_session_id"))
        if session_id not in session_ids or _text(row.get("error")):
            continue
        interaction_user_id = _text(row.get("user_id"))
        if interaction_user_id and interaction_user_id != user_id:
            continue
        previous = latest_by_session.get(session_id)
        if previous is None or _interaction_sort_key(row) > _interaction_sort_key(previous):
            latest_by_session[session_id] = row

    for row in result.values():
        session_id = _text(row.get("scenario_session_id"))
        interaction = latest_by_session.get(session_id)
        if not interaction:
            continue
        row["last_user_text"] = _text(interaction.get("user_text"))
        row["last_mary_response"] = _text(interaction.get("mary_response"))
        row["last_interaction_number"] = _int(interaction.get("interaction_number"), 0)
        row["last_interaction_timestamp"] = _text(
            interaction.get("timestamp") or interaction.get("updated_at")
        )

    return result


def catalog_story_state(row: dict[str, Any] | None) -> str:
    if not isinstance(row, dict):
        return "new"
    status = (_text(row.get("status")) or "active").lower()
    active = _bool(row.get("active"), status == "active")
    input_locked = _bool(row.get("input_locked"), False)
    ending_sent = _bool(row.get("ending_sent"), False)
    if status == "active" and active and not input_locked and not ending_sent:
        return "active"
    return "finished"


def hydrate_story_session(row: dict[str, Any]) -> StorySession:
    """Reconstrói o StorySession persistido em story_progress_json."""
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

    if not payload["access_id"] or not payload["story_id"]:
        raise ValueError("A sessão persistida não possui identificadores obrigatórios.")
    if not payload["chapter_id"] or not payload["current_beat"]:
        raise ValueError("A sessão persistida não possui capítulo ou beat atual.")

    payload.setdefault("completed_beats", list(progress.get("completed_beats") or []))
    payload.setdefault("completed_facts", list(progress.get("completed_facts") or []))
    payload.setdefault("current_beat_emitted", False)
    payload.setdefault("alignment_warning_active", False)
    payload.setdefault("alignment_warning_reason", "")
    return StorySession(**payload)


__all__ = [
    "catalog_story_state",
    "hydrate_story_session",
    "latest_story_sessions_by_scenario",
]
